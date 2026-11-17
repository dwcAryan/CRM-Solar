import logging
from datetime import datetime, time, timedelta

from django.utils import timezone

from accounts.models import User
from leads.models import Lead
from messaging.providers import get_whatsapp_provider
from notifications.models import Notification
from surveys.models import Survey

logger = logging.getLogger(__name__)


def notify_salespersons_daily_followups(now=None) -> list[Notification]:
    """
    Daily Job 1 (Runs at 09:00 Asia/Kolkata):
    Notifies each active salesperson of their follow-ups due today and overdue.
    """
    if now is None:
        local_now = timezone.localtime()
    else:
        local_now = timezone.localtime(now) if timezone.is_aware(now) else now

    today_date = local_now.date()
    today_start = timezone.make_aware(datetime.combine(today_date, time.min))
    today_end = timezone.make_aware(datetime.combine(today_date, time.max))

    created_notifications = []
    salespeople = User.objects.filter(role=User.Role.SALESPERSON, is_active=True)

    for sp in salespeople:
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
        if total > 0:
            greeting = f"Good morning {sp.first_name or sp.username}!"
            msg = f"{greeting} You have {due_today_count} follow-ups due today and {overdue_count} overdue."
            notif = Notification.objects.create(
                user=sp,
                message=msg,
                link="/leads/today",
            )
            created_notifications.append(notif)
            logger.info(f"Created followup reminder for salesperson {sp.username}: {msg}")

    return created_notifications


def remind_surveys_scheduled_tomorrow(now=None) -> dict:
    """
    Daily Job 2 (Runs at 18:00 Asia/Kolkata):
    Sends reminders for site surveys scheduled tomorrow:
    1. Notifies the surveyor.
    2. Notifies the salesperson.
    3. Sends the customer a WhatsApp template message (if do_not_contact is False).
    """
    if now is None:
        local_now = timezone.localtime()
    else:
        local_now = timezone.localtime(now) if timezone.is_aware(now) else now

    tomorrow_date = local_now.date() + timedelta(days=1)
    tomorrow_start = timezone.make_aware(datetime.combine(tomorrow_date, time.min))
    tomorrow_end = timezone.make_aware(datetime.combine(tomorrow_date, time.max))

    surveys = Survey.objects.filter(
        scheduled_at__gte=tomorrow_start,
        scheduled_at__lte=tomorrow_end,
        status__in=[Survey.Status.BOOKED, Survey.Status.RESCHEDULED],
    ).select_related('lead', 'surveyor', 'lead__assigned_to')

    whatsapp = get_whatsapp_provider()
    notifs_created = 0
    messages_sent = 0

    for s in surveys:
        formatted_time = timezone.localtime(s.scheduled_at).strftime('%I:%M %p')
        lead = s.lead

        # 1. Notify Surveyor
        if s.surveyor:
            Notification.objects.create(
                user=s.surveyor,
                message=f"Reminder: Site survey for {lead.name} is scheduled tomorrow at {formatted_time} ({lead.city}).",
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

        # 3. Send WhatsApp to Customer (respects do_not_contact)
        sent = whatsapp.send_template(
            phone=lead.phone,
            template_name='survey_reminder',
            params={
                'customer_name': lead.name,
                'time': formatted_time,
                'address': lead.address or lead.city or 'your registered location',
            },
            lead=lead,
        )
        if sent:
            messages_sent += 1

    return {
        "surveys_processed": len(surveys),
        "notifications_created": notifs_created,
        "messages_sent": messages_sent,
    }
