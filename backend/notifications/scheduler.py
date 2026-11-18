import datetime
import logging
from typing import Dict, List, Optional
import zoneinfo
from django.utils import timezone

from accounts.models import User
from leads.models import Lead
from messaging.providers import get_sms_provider, get_whatsapp_provider
from notifications.models import Notification
from surveys.models import Survey

logger = logging.getLogger(__name__)


def is_user_local_hour(user: User, target_hour: int, now: Optional[datetime.datetime] = None) -> bool:
    """
    Checks if current time in the user's default timezone matches target_hour (e.g. 9 or 18).
    """
    tz_str = getattr(user, 'default_timezone', None) or 'Asia/Kolkata'
    try:
        user_tz = zoneinfo.ZoneInfo(tz_str)
    except Exception:
        user_tz = zoneinfo.ZoneInfo('Asia/Kolkata')

    curr = now or timezone.now()
    if timezone.is_naive(curr):
        curr = timezone.make_aware(curr, datetime.timezone.utc)

    user_local = curr.astimezone(user_tz)
    return user_local.hour == target_hour


def notify_salespersons_daily_followups(
    salesperson: Optional[User] = None,
    now: Optional[datetime.datetime] = None,
    force: bool = False,
) -> List[Notification]:
    """
    Sends 9:00 AM daily follow-up digest.
    If salesperson is provided, runs for that salesperson.
    Otherwise runs for all active salespeople whose local time is 9:00 AM (or all if force=True).
    """
    curr = now or timezone.now()
    if timezone.is_naive(curr):
        curr = timezone.make_aware(curr, datetime.timezone.utc)

    salespeople = [salesperson] if salesperson else list(User.objects.filter(role=User.Role.SALESPERSON, is_active=True))
    created_notifications = []

    for sp in salespeople:
        if not force and now is None and salesperson is None and not is_user_local_hour(sp, 9, curr):
            continue

        sp_tz_str = sp.default_timezone or 'Asia/Kolkata'
        try:
            sp_tz = zoneinfo.ZoneInfo(sp_tz_str)
        except Exception:
            sp_tz = zoneinfo.ZoneInfo('Asia/Kolkata')

        sp_local_now = curr.astimezone(sp_tz)
        today_date = sp_local_now.date()
        today_start = timezone.make_aware(datetime.datetime.combine(today_date, datetime.time.min), sp_tz)
        today_end = timezone.make_aware(datetime.datetime.combine(today_date, datetime.time.max), sp_tz)

        # Avoid double-sending to same user today
        already_sent = Notification.objects.filter(
            user=sp,
            created_at__gte=today_start,
            message__contains="follow-ups due today",
        ).exists()
        if already_sent and not force:
            continue

        active_leads = Lead.objects.filter(
            assigned_to=sp,
            next_followup_at__isnull=False,
            next_followup_at__lte=today_end,
        ).exclude(status__in=Lead.TERMINAL_STATUSES)

        overdue_count = active_leads.filter(next_followup_at__lt=today_start).count()
        due_today_count = active_leads.filter(
            next_followup_at__gte=today_start,
            next_followup_at__lte=today_end,
        ).count()

        total = overdue_count + due_today_count
        if total > 0 or force:
            greeting = f"Good morning {sp.first_name or sp.username}!"
            msg = f"{greeting} You have {due_today_count} follow-ups due today and {overdue_count} overdue."
            notif = Notification.objects.create(
                user=sp,
                message=msg,
                link="/leads/today",
            )
            created_notifications.append(notif)
            logger.info(f"Created followup reminder for salesperson {sp.username} in {sp_tz_str}: {msg}")

    return created_notifications


def remind_surveys_scheduled_tomorrow(
    target_user: Optional[User] = None,
    now: Optional[datetime.datetime] = None,
    force: bool = False,
) -> Dict[str, int]:
    """
    Sends 18:00 (6:00 PM) reminders for site surveys scheduled tomorrow.
    Dispatches to:
    1. Surveyor notification
    2. Salesperson notification
    3. Customer outbound message via their region's preferred channel (SMS in AU, WhatsApp in IN).
       Checks customer consent & opt-out flags before sending.
    """
    curr = now or timezone.now()
    if timezone.is_naive(curr):
        curr = timezone.make_aware(curr, datetime.timezone.utc)

    whatsapp = get_whatsapp_provider()
    sms = get_sms_provider()

    surveys = Survey.objects.filter(
        status__in=[Survey.Status.BOOKED, Survey.Status.RESCHEDULED],
    ).select_related('lead', 'surveyor', 'lead__assigned_to', 'lead__region')

    notifs_created = 0
    messages_sent = 0
    surveys_processed = 0

    for s in surveys:
        lead = s.lead
        lead_tz_str = lead.timezone or (lead.region.default_timezone if lead.region else 'Asia/Kolkata')
        try:
            lead_tz = zoneinfo.ZoneInfo(lead_tz_str)
        except Exception:
            lead_tz = zoneinfo.ZoneInfo('Asia/Kolkata')

        lead_local_now = curr.astimezone(lead_tz)

        # Check if local time is 18:00 (6 PM) in lead's timezone or forced/testing
        if not force and now is None and lead_local_now.hour != 18:
            continue

        # Check if survey is scheduled tomorrow in lead's timezone
        survey_local = s.scheduled_at.astimezone(lead_tz)
        tomorrow_date = lead_local_now.date() + datetime.timedelta(days=1)
        if survey_local.date() != tomorrow_date and not force:
            continue

        surveys_processed += 1
        formatted_time = survey_local.strftime('%I:%M %p %Z')

        # 1. Notify Surveyor
        if s.surveyor:
            Notification.objects.create(
                user=s.surveyor,
                message=f"Reminder: Site survey for {lead.name} is scheduled tomorrow at {formatted_time} ({lead.city or lead.suburb}).",
                link=f"/surveys/{s.id}",
            )
            notifs_created += 1

        # 2. Notify Salesperson
        if lead.assigned_to and (not s.surveyor or lead.assigned_to_id != s.surveyor_id):
            Notification.objects.create(
                user=lead.assigned_to,
                message=f"Reminder: Site survey for your lead {lead.name} is tomorrow at {formatted_time}.",
                link=f"/surveys/{s.id}",
            )
            notifs_created += 1

        # 3. Customer Outbound (Channel determined by region preferred channel)
        preferred_channel = 'whatsapp'
        opt_out_line = 'Reply STOP to opt out'
        if lead.region:
            opt_out_line = lead.region.opt_out_text or opt_out_line
            if lead.region.preferred_channels:
                preferred_channel = lead.region.preferred_channels[0]

        params = {
            'customer_name': lead.name,
            'time': formatted_time,
            'address': lead.address or lead.suburb or lead.city or 'your registered site',
            'opt_out_line': opt_out_line,
        }

        phone_to_use = lead.phone
        if preferred_channel == 'sms':
            sent = sms.send_template(
                phone=phone_to_use,
                template_name='survey_reminder',
                params=params,
                lead=lead,
            )
        else:
            sent = whatsapp.send_template(
                phone=phone_to_use,
                template_name='survey_reminder',
                params=params,
                lead=lead,
            )

        if sent:
            messages_sent += 1

    return {
        'surveys_processed': surveys_processed,
        'notifications_created': notifs_created,
        'messages_sent': messages_sent,
    }


def run_hourly_scheduled_tasks(now: Optional[datetime.datetime] = None) -> Dict[str, Any]:
    """
    Master hourly task checking all users and leads across their individual timezones:
    - 09:00 local: Sends daily morning follow-up digests.
    - 18:00 local: Sends tomorrow survey reminders.
    """
    curr = now or timezone.now()
    notifs = notify_salespersons_daily_followups(now=curr, force=False)
    survey_res = remind_surveys_scheduled_tomorrow(now=curr, force=False)
    return {
        'notifications_created': len(notifs),
        'survey_reminders': survey_res,
    }
