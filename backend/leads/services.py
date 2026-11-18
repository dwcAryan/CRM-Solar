from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone

from accounts.models import User
from accounts.permissions import can_user_mark_lost
from activities.models import Activity
from masters.models import LostReason, NurtureReason, Outcome, PolicySettings

from .models import Lead, LeadStatusHistory


@transaction.atomic
def process_log_activity(
    lead: Lead,
    user: User,
    data: Dict[str, Any],
    ip_address: Optional[str] = None,
) -> Tuple[Activity, Lead]:
    """
    Executes core business logic for logging an activity on a lead:
    1. Blocks 'call', 'whatsapp', or 'sms' if do_not_contact is True or specific channel opted out.
    2. Evaluates calling hours for 'call' activities (warn with required override reason or block).
    3. Replaces dynamic tokens like {channel} and {incentive_label} in next actions.
    4. Enforces retry rules for 'No answer' (Attempting contact -> Unreachable -> Lost).
    5. Validates required follow-up dates on non-terminal statuses.
    6. Validates LostReason and NurtureReason requirements.
    7. Checks WHO_CAN_MARK_LOST permissions.
    8. Atomically creates Activity, records LeadStatusHistory, updates Lead, and writes AuditLog where necessary.
    """
    activity_type = data.get('type')
    outcome_id = data.get('outcome_id')
    notes = data.get('notes', '')
    remark = (data.get('remark') or notes or '').strip()[:500]

    # 1. Do not contact validation & channel opt-outs
    if lead.do_not_contact and activity_type in ['call', 'whatsapp', 'sms']:
        raise ValidationError(
            {"detail": "This lead has requested 'Do not contact'. Calls, WhatsApp, and SMS messages are blocked."}
        )

    if activity_type == 'call' and lead.opt_out_calls:
        raise ValidationError(
            {"detail": "This lead has explicitly opted out of telephone calls."}
        )
    if activity_type == 'whatsapp' and lead.opt_out_whatsapp:
        raise ValidationError(
            {"detail": "This lead has explicitly opted out of WhatsApp communications."}
        )
    if activity_type == 'sms' and lead.opt_out_sms:
        raise ValidationError(
            {"detail": "This lead has explicitly opted out of SMS text messages."}
        )

    # 2. Calling hours check for outbound calls
    if activity_type == 'call':
        from .timezone_utils import check_calling_hours
        is_allowed, reason = check_calling_hours(lead)
        if not is_allowed:
            policy = 'warn'
            if lead.region and hasattr(lead.region, 'calling_hours_policy'):
                policy = lead.region.calling_hours_policy

            if policy == 'block':
                raise ValidationError({
                    "detail": f"Outbound call blocked by region calling policy: {reason}"
                })
            else:  # 'warn'
                override_reason = (data.get('calling_hours_override_reason') or '').strip()
                if not override_reason:
                    raise ValidationError({
                        "outside_hours": True,
                        "detail": f"Call attempted outside permitted calling hours: {reason} A typed override reason is required to proceed.",
                    })
                else:
                    # Log override in AuditLog
                    from .models import AuditLog
                    AuditLog.objects.create(
                        user=user,
                        action='calling_hours_override',
                        lead=lead,
                        reason=override_reason,
                        details={
                            'restriction_reason': reason,
                            'activity_type': activity_type,
                            'lead_timezone': lead.timezone or (lead.region.default_timezone if lead.region else 'UTC'),
                        },
                        ip_address=ip_address,
                    )

    outcome: Optional[Outcome] = None
    if outcome_id:
        try:
            outcome = Outcome.objects.get(id=outcome_id)
        except Outcome.DoesNotExist:
            raise ValidationError({"outcome_id": "Specified outcome does not exist."})

    policy = PolicySettings.load()

    # Determine base values from outcome
    target_status = data.get('status') or (outcome.default_status if outcome else lead.status)
    target_next_action = data.get('next_action') or (outcome.default_next_action if outcome else lead.next_action)
    target_followup_at = data.get('next_followup_at')

    # Resolve Lost and Nurture reasons
    lost_reason: Optional[LostReason] = None
    lost_reason_id = data.get('lost_reason_id')
    if lost_reason_id:
        lost_reason = LostReason.objects.filter(id=lost_reason_id).first()
    elif lead.lost_reason:
        lost_reason = lead.lost_reason

    nurture_reason: Optional[NurtureReason] = None
    nurture_reason_id = data.get('nurture_reason_id')
    if nurture_reason_id:
        nurture_reason = NurtureReason.objects.filter(id=nurture_reason_id).first()
    elif lead.nurture_reason:
        nurture_reason = lead.nurture_reason

    now = timezone.now()

    # Determine region-specific channel and incentive labels for placeholders
    preferred_channel = "WhatsApp"
    incentive_label = "Subsidy"
    if lead.region:
        raw_pref = lead.region.preferred_channels
        if isinstance(raw_pref, list):
            pref = [str(c).strip().title() for c in raw_pref if str(c).strip()]
        else:
            pref = [c.strip().title() for c in str(raw_pref or '').split(',') if c.strip()]
        if pref:
            preferred_channel = pref[0]
        elif lead.region_id == 'AU':
            preferred_channel = "SMS"
        if lead.region.incentive_label:
            incentive_label = lead.region.incentive_label

    # 3. Retry rule for "No answer"
    is_no_answer = outcome and outcome.name.strip().lower() == 'no answer'
    is_no_answer_on_unreachable = False

    if is_no_answer:
        if lead.status == Lead.Status.UNREACHABLE:
            # If an Unreachable lead gets another "No answer", close it as Lost with reason "no response"
            is_no_answer_on_unreachable = True
            target_status = Lead.Status.LOST
            target_next_action = "Closed as Lost after repeated unanswered calls"
            target_followup_at = None
            no_response_reason = LostReason.objects.filter(name__iexact='no response').first()
            if no_response_reason:
                lost_reason = no_response_reason
        else:
            lead.attempt_count += 1
            max_attempts = policy.max_call_attempts_before_unreachable
            unreachable_days = policy.unreachable_followup_days

            if lead.attempt_count >= max_attempts:
                target_status = Lead.Status.UNREACHABLE
                target_next_action = "Unreachable follow-up"
                target_followup_at = now + timedelta(days=unreachable_days)
            else:
                target_status = Lead.Status.ATTEMPTING_CONTACT
                if lead.attempt_count == 1:
                    target_next_action = f"Retry, then send a {preferred_channel} message"
                    target_followup_at = now + timedelta(hours=4)
                elif lead.attempt_count == 2:
                    target_next_action = "Retry at a different time"
                    target_followup_at = now + timedelta(days=1)
                else:  # attempts 3 and 4
                    target_next_action = f"Retry on later day, one more {preferred_channel} message"
                    target_followup_at = now + timedelta(days=2)
    else:
        # Reset attempt_count when a call is answered
        if activity_type == 'call' and outcome and outcome.name.strip().lower() not in ['no answer', 'busy or switched off']:
            lead.attempt_count = 0

        # Calculate default follow-up if not provided and not a No answer rule
        if not target_followup_at and outcome and outcome.default_followup_days is not None:
            if outcome.default_followup_days == 0:
                target_followup_at = now + timedelta(hours=4)
            else:
                target_followup_at = now + timedelta(days=outcome.default_followup_days)

    # Replace dynamic tokens in target_next_action
    if target_next_action:
        target_next_action = target_next_action.replace('{channel}', preferred_channel).replace('{incentive_label}', incentive_label)

    # 4. Terminal status handling
    is_terminal = target_status in Lead.TERMINAL_STATUSES
    if is_terminal:
        target_followup_at = None
    elif not target_followup_at:
        raise ValidationError(
            {"next_followup_at": "Next follow-up date and time is required for non-terminal statuses."}
        )

    # 5. Reason validations & Lost Approval Pending flow
    if target_status == Lead.Status.LOST:
        if not lost_reason:
            raise ValidationError({"lost_reason_id": "A lost reason is required when marking a lead as Lost."})

        # Salespeople cannot finalize Lost; puts lead into Lost approval pending
        if getattr(user, 'role', None) == 'salesperson' and not getattr(user, 'is_superuser', False):
            target_status = Lead.Status.LOST_APPROVAL_PENDING
            lead.lost_pending_reason = lost_reason
            lead.lost_pending_notes = notes or remark
            lead.previous_status_before_lost = lead.status
            target_next_action = "Awaiting manager Lost approval"
            target_followup_at = now + timedelta(days=2)  # Non-terminal, so follow-up required
            is_terminal = False

            # Notify managers of pending approval
            from accounts.models import User as AppUser
            from notifications.models import Notification
            mgr_qs = AppUser.objects.filter(role__in=[AppUser.Role.MANAGER, AppUser.Role.ADMIN], is_active=True)
            if lead.region_id:
                mgr_qs = mgr_qs.filter(models.Q(allowed_regions__code=lead.region_id) | models.Q(is_superuser=True)).distinct()
            for mgr in mgr_qs:
                Notification.objects.create(
                    user=mgr,
                    message=f"Lead '{lead.name}' submitted for Lost approval by {user.get_full_name() or user.username}.",
                    link=f"/leads/{lead.id}",
                )
        else:
            # Permission check: WHO_CAN_MARK_LOST (applies to direct marking by managers/admins)
            if not is_no_answer_on_unreachable and lead.status != Lead.Status.LOST and not can_user_mark_lost(user):
                raise PermissionDenied(
                    f"Your role ({user.role}) does not have permission to mark leads as Lost. "
                    f"Policy requires role '{policy.who_can_mark_lost}' or higher."
                )

    if target_status == Lead.Status.NURTURE and not nurture_reason:
        raise ValidationError({"nurture_reason_id": "A nurture reason is required when placing a lead into Nurture."})

    # 6. Do not contact flag
    if target_status == Lead.Status.DO_NOT_CONTACT:
        lead.do_not_contact = True

    # 7. Won milestone
    if target_status == Lead.Status.WON:
        lead.won_at = now

    old_status = lead.status

    # 8. Create Activity
    activity = Activity.objects.create(
        lead=lead,
        type=activity_type,
        outcome=outcome,
        notes=notes,
        remark=remark,
        status_after=target_status,
        next_action=target_next_action,
        next_followup_at=target_followup_at,
        created_by=user,
    )

    # 9. Record Status History if status changed
    if old_status != target_status:
        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=user,
            note=notes or f"Status changed from {old_status} to {target_status} via {activity_type}",
            remark=remark,
        )

    # 10. Update Lead
    lead.status = target_status
    lead.next_action = target_next_action
    lead.next_followup_at = target_followup_at
    lead.lost_reason = lost_reason
    lead.nurture_reason = nurture_reason
    if remark:
        lead.remark = remark
    lead.save()

    return activity, lead
