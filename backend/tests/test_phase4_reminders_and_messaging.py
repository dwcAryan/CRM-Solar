from datetime import datetime, time, timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from leads.models import Lead
from messaging.models import MessageLog
from messaging.providers import get_whatsapp_provider
from notifications.models import Notification
from notifications.scheduler import (
    notify_salespersons_daily_followups,
    remind_surveys_scheduled_tomorrow,
)
from surveys.models import Survey


@pytest.fixture(autouse=True)
def setup_data(db):
    call_command('seed_masters')
    call_command('seed_templates')


@pytest.fixture
def salesperson(db):
    user, _ = User.objects.get_or_create(
        username='sales_rep_1',
        defaults={'email': 'rep1@test.com', 'role': User.Role.SALESPERSON, 'first_name': 'Aakash'}
    )
    user.set_password('Password123!')
    user.save()
    return user


@pytest.fixture
def surveyor(db):
    user, _ = User.objects.get_or_create(
        username='surveyor_1',
        defaults={'email': 'surv1@test.com', 'role': User.Role.SURVEYOR, 'first_name': 'Ketan'}
    )
    user.set_password('Password123!')
    user.save()
    return user


@pytest.mark.django_db
class TestPhase4RemindersAndMessaging:

    def test_daily_salesperson_followup_reminder_job(self, salesperson):
        """Daily 9:00 job: notifies salesperson of follow-ups due today and overdue."""
        now = timezone.localtime()
        today_date = now.date()

        # Lead 1: Overdue (yesterday)
        Lead.objects.create(
            name='Overdue Customer',
            phone='9800011111',
            status=Lead.Status.ATTEMPTING_CONTACT,
            assigned_to=salesperson,
            next_followup_at=now - timedelta(days=1),
        )

        # Lead 2: Due today (later today)
        Lead.objects.create(
            name='Today Customer',
            phone='9800022222',
            status=Lead.Status.FOLLOW_UP,
            assigned_to=salesperson,
            next_followup_at=timezone.make_aware(datetime.combine(today_date, time(14, 0))),
        )

        # Lead 3: Terminal (Won) with past date -> should be excluded
        Lead.objects.create(
            name='Won Customer',
            phone='9800033333',
            status=Lead.Status.WON,
            assigned_to=salesperson,
            next_followup_at=now - timedelta(days=2),
        )

        # Call job directly
        notifications = notify_salespersons_daily_followups(now=now)

        assert len(notifications) >= 1
        rep_notif = Notification.objects.filter(user=salesperson).first()
        assert rep_notif is not None
        assert "1 follow-ups due today and 1 overdue" in rep_notif.message
        assert rep_notif.link == "/leads/today"
        assert rep_notif.is_read is False

    def test_daily_survey_tomorrow_reminder_job(self, salesperson, surveyor):
        """Daily 18:00 job: notifies surveyor and salesperson, sends customer WhatsApp reminder."""
        now = timezone.localtime()
        tomorrow_date = now.date() + timedelta(days=1)
        survey_time = timezone.make_aware(datetime.combine(tomorrow_date, time(11, 30)))

        lead = Lead.objects.create(
            name='Terrace Owner',
            phone='9825988888',
            city='Vadodara',
            address='12, Shanti Nagar, Alkapuri',
            status=Lead.Status.SURVEY_SCHEDULED,
            assigned_to=salesperson,
            do_not_contact=False,
        )

        Survey.objects.create(
            lead=lead,
            surveyor=surveyor,
            scheduled_at=survey_time,
            status=Survey.Status.BOOKED,
        )

        # Clear prior logs/notifs
        Notification.objects.all().delete()
        MessageLog.objects.all().delete()

        # Call job directly
        res = remind_surveys_scheduled_tomorrow(now=now)

        assert res['surveys_processed'] == 1
        assert res['messages_sent'] == 1

        # Check surveyor notification
        surveyor_notif = Notification.objects.filter(user=surveyor).first()
        assert surveyor_notif is not None
        assert "Site survey for Terrace Owner is scheduled tomorrow" in surveyor_notif.message

        # Check salesperson notification
        sales_notif = Notification.objects.filter(user=salesperson).first()
        assert sales_notif is not None
        assert "Site survey for your lead Terrace Owner is tomorrow" in sales_notif.message

        # Check MessageLog
        msg_log = MessageLog.objects.filter(phone='9825988888').first()
        assert msg_log is not None
        assert msg_log.template_name == 'survey_reminder'
        assert msg_log.status == MessageLog.Status.SENT
        assert "Terrace Owner" in msg_log.message_text

    def test_never_send_to_do_not_contact_leads(self, salesperson, surveyor):
        """WhatsApp provider must never send to leads with do_not_contact=true."""
        now = timezone.localtime()
        tomorrow_date = now.date() + timedelta(days=1)
        survey_time = timezone.make_aware(datetime.combine(tomorrow_date, time(15, 0)))

        lead = Lead.objects.create(
            name='Blocked Contact',
            phone='9825977777',
            city='Ahmedabad',
            status=Lead.Status.DO_NOT_CONTACT,
            assigned_to=salesperson,
            do_not_contact=True,
        )

        Survey.objects.create(
            lead=lead,
            surveyor=surveyor,
            scheduled_at=survey_time,
            status=Survey.Status.BOOKED,
        )

        MessageLog.objects.all().delete()

        # Call job
        remind_surveys_scheduled_tomorrow(now=now)

        # MessageLog should reflect blocked status
        log = MessageLog.objects.filter(phone='9825977777').first()
        assert log is not None
        assert log.status == MessageLog.Status.BLOCKED
        assert "do_not_contact=True" in log.error_message

        # Direct provider test
        provider = get_whatsapp_provider()
        res = provider.send_text(phone=lead.phone, text="Hello", lead=lead)
        assert res is False

    def test_notification_endpoints(self, salesperson):
        """Test notification listing, marking read, and unread count."""
        notif1 = Notification.objects.create(user=salesperson, message='Notification 1', is_read=False)
        notif2 = Notification.objects.create(user=salesperson, message='Notification 2', is_read=False)

        client = APIClient()
        client.force_authenticate(user=salesperson)

        # Unread count
        res = client.get('/api/notifications/unread-count/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['unread_count'] == 2

        # Mark read single
        res = client.post(f'/api/notifications/{notif1.id}/mark-read/')
        assert res.status_code == status.HTTP_200_OK
        notif1.refresh_from_db()
        assert notif1.is_read is True

        # Unread count after 1 read
        res = client.get('/api/notifications/unread-count/')
        assert res.data['unread_count'] == 1

        # Mark all read
        res = client.post('/api/notifications/mark-all-read/')
        assert res.status_code == status.HTTP_200_OK
        notif2.refresh_from_db()
        assert notif2.is_read is True

        res = client.get('/api/notifications/unread-count/')
        assert res.data['unread_count'] == 0
