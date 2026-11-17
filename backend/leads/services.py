from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
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
) -> Tuple[Activity, Lead]:
    """
    Executes core business logic for logging an activity on a lead:
    1. Blocks 'call' or 'whatsapp' if do_not_contact is True.
    2. Applies outcome defaults or custom overrides.
    3. Enforces retry rules for 'No answer' (Attempting contact -> Unreachable -> Lost).
    4. Validates required follow-up dates on non-terminal statuses.
    5. Validates LostReason and NurtureReason requirements.
    6. Checks WHO_CAN_MARK_LOST permissions.
    7. Atomically creates Activity, records LeadStatusHistory, and updates the Lead.
    """
    activity_type = data.get('type')
    outcome_id = data.get('outcome_id')
    notes = data.get('notes', '')

    # 1. Do not contact validation
    if lead.do_not_contact and activity_type in ['call', 'whatsapp']:
        raise ValidationError(
            {"detail": "This lead has requested 'Do not contact'. Calls and WhatsApp messages are blocked."}
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

    # 2. Retry rule for "No answer"
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
                    target_next_action = "Retry, then send a WhatsApp message"
                    target_followup_at = now + timedelta(hours=4)
                elif lead.attempt_count == 2:
                    target_next_action = "Retry at a different time"
                    target_followup_at = now + timedelta(days=1)
                else:  # attempts 3 and 4
                    target_next_action = "Retry on later day, one more WhatsApp message"
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

    # 3. Terminal status handling
    is_terminal = target_status in Lead.TERMINAL_STATUSES
    if is_terminal:
        target_followup_at = None
    elif not target_followup_at:
        raise ValidationError(
            {"next_followup_at": "Next follow-up date and time is required for non-terminal statuses."}
        )

    # 4. Reason validations
    if target_status == Lead.Status.LOST:
        if not lost_reason:
            raise ValidationError({"lost_reason_id": "A lost reason is required when marking a lead as Lost."})

        # Permission check: WHO_CAN_MARK_LOST (applies to manual marking, not auto-close from Unreachable)
        if not is_no_answer_on_unreachable and lead.status != Lead.Status.LOST and not can_user_mark_lost(user):
            raise PermissionDenied(
                f"Your role ({user.role}) does not have permission to mark leads as Lost. "
                f"Policy requires role '{policy.who_can_mark_lost}' or higher."
            )

    if target_status == Lead.Status.NURTURE and not nurture_reason:
        raise ValidationError({"nurture_reason_id": "A nurture reason is required when placing a lead into Nurture."})

    # 5. Do not contact flag
    if target_status == Lead.Status.DO_NOT_CONTACT:
        lead.do_not_contact = True

    # 6. Won milestone
    if target_status == Lead.Status.WON:
        lead.won_at = now

    old_status = lead.status

    # 7. Create Activity
    activity = Activity.objects.create(
        lead=lead,
        type=activity_type,
        outcome=outcome,
        notes=notes,
        status_after=target_status,
        next_action=target_next_action,
        next_followup_at=target_followup_at,
        created_by=user,
    )

    # 8. Record Status History if status changed
    if old_status != target_status:
        LeadStatusHistory.objects.create(
            lead=lead,
            old_status=old_status,
            new_status=target_status,
            changed_by=user,
            note=notes or f"Status changed from {old_status} to {target_status} via {activity_type}",
        )

    # 9. Update Lead
    lead.status = target_status
    lead.next_action = target_next_action
    lead.next_followup_at = target_followup_at
    lead.lost_reason = lost_reason
    lead.nurture_reason = nurture_reason
    lead.save()

    return activity, lead
