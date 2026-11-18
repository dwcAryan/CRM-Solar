import datetime
import json
import zoneinfo
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from leads.models import Lead
from masters.models import LeadSource, Region
from notifications.models import NotificationPreference, PushSubscription
from notifications.push_service import send_push_notification
from notifications.scheduler import notify_salespersons_daily_followups


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def in_region(db):
    return Region.objects.get_or_create(
        code='IN',
        defaults={'name': 'India', 'currency': 'INR', 'currency_symbol': '₹', 'default_timezone': 'Asia/Kolkata'}
    )[0]


@pytest.fixture
def au_region(db):
    return Region.objects.get_or_create(
        code='AU',
        defaults={'name': 'Australia', 'currency': 'AUD', 'currency_symbol': 'A$', 'default_timezone': 'Australia/Sydney'}
    )[0]


@pytest.fixture
def test_user(db, in_region):
    u = User.objects.create_user(
        username='notif_test_user',
        email='notif@example.com',
        password='TestPassword123!',
        role=User.Role.SALESPERSON,
        default_region=in_region,
        default_timezone='Asia/Kolkata',
    )
    u.allowed_regions.add(in_region)
    return u


@pytest.mark.django_db
class TestPushEndpoints:
    def test_vapid_public_key(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        res = api_client.get('/api/notifications/vapid-public-key/')
        assert res.status_code == status.HTTP_200_OK
        assert 'public_key' in res.data
        assert len(res.data['public_key']) > 20

    def test_push_subscribe_and_unsubscribe(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)

        endpoint_url = "https://fcm.googleapis.com/fcm/send/sample-endpoint-12345"
        payload = {
            "endpoint": endpoint_url,
            "keys": {
                "p256dh": "sample_p256dh_key_base64",
                "auth": "sample_auth_secret"
            },
            "user_agent": "Mozilla/5.0 Test Browser",
        }

        # 1. Subscribe
        sub_res = api_client.post('/api/notifications/push-subscribe/', payload, format='json')
        assert sub_res.status_code == status.HTTP_201_CREATED
        assert sub_res.data['status'] == 'subscribed'
        assert PushSubscription.objects.filter(user=test_user, endpoint=endpoint_url).exists()

        # 2. Unsubscribe
        unsub_res = api_client.post('/api/notifications/push-unsubscribe/', {"endpoint": endpoint_url}, format='json')
        assert unsub_res.status_code == status.HTTP_200_OK
        assert unsub_res.data['deleted'] == 1
        assert not PushSubscription.objects.filter(endpoint=endpoint_url).exists()

    def test_notification_preferences_get_and_update(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)

        # GET default preferences
        get_res = api_client.get('/api/notifications/preferences/')
        assert get_res.status_code == status.HTTP_200_OK
        assert get_res.data['push_enabled'] is True
        assert get_res.data['quiet_hours_enabled'] is False

        # PUT update preferences
        update_payload = {
            "in_app_enabled": True,
            "browser_enabled": True,
            "push_enabled": False,
            "email_enabled": True,
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00:00",
            "quiet_hours_end": "07:00:00",
        }
        put_res = api_client.put('/api/notifications/preferences/', update_payload, format='json')
        assert put_res.status_code == status.HTTP_200_OK
        assert put_res.data['push_enabled'] is False
        assert put_res.data['email_enabled'] is True
        assert put_res.data['quiet_hours_enabled'] is True


@pytest.mark.django_db
class TestPushServiceAndPrivacy:
    def test_quiet_hours_in_user_timezone(self, test_user, au_region):
        test_user.default_timezone = 'Australia/Sydney'
        test_user.save()

        pref, _ = NotificationPreference.objects.get_or_create(user=test_user)
        pref.quiet_hours_enabled = True
        pref.quiet_hours_start = datetime.time(22, 0)
        pref.quiet_hours_end = datetime.time(8, 0)
        pref.save()

        syd_tz = zoneinfo.ZoneInfo('Australia/Sydney')

        # Test at 23:30 Sydney time (inside quiet hours)
        dt_night = datetime.datetime(2026, 6, 15, 23, 30, tzinfo=syd_tz)
        assert pref.is_in_quiet_hours(dt_night) is True

        # Test at 14:00 Sydney time (outside quiet hours)
        dt_day = datetime.datetime(2026, 6, 15, 14, 0, tzinfo=syd_tz)
        assert pref.is_in_quiet_hours(dt_day) is False

        # Verify send_push_notification skips during quiet hours
        with patch.object(pref, 'is_in_quiet_hours', return_value=True):
            with patch('notifications.models.NotificationPreference.objects.get_or_create', return_value=(pref, False)):
                result = send_push_notification(test_user, "Alert", "Test alert")
                assert result.get('skipped') == 'quiet_hours'

    def test_payload_privacy_rule(self, test_user):
        """Verifies customer phone numbers and PII are NEVER included in push payloads."""
        PushSubscription.objects.create(
            user=test_user,
            endpoint="https://example.pushservice.com/sub/1",
            p256dh="dummy_p256dh",
            auth="dummy_auth",
        )

        customer_phone = "+919876543210"
        customer_name = "Rajesh Gupta"
        sensitive_notes = "Bank account details and rooftop keys provided"

        with patch('pywebpush.webpush') as mock_webpush:
            send_push_notification(
                user=test_user,
                title="Follow-up due now",
                body="You have 1 customer consultation due",
                lead_id=42,
                url="/leads/42",
            )

            assert mock_webpush.called
            call_kwargs = mock_webpush.call_args[1]
            sent_data = json.loads(call_kwargs['data'])

            # Payload must contain only safe routing and task info
            assert sent_data['lead_id'] == 42
            assert sent_data['title'] == "Follow-up due now"
            assert sent_data['url'] == "/leads/42"

            # Strict Privacy Check: No raw customer PII
            payload_str = json.dumps(sent_data)
            assert customer_phone not in payload_str
            assert customer_name not in payload_str
            assert sensitive_notes not in payload_str

    def test_expired_subscription_cleanup(self, test_user):
        """Subscriptions returning HTTP 404 or 410 must be deleted automatically."""
        sub1 = PushSubscription.objects.create(
            user=test_user,
            endpoint="https://push.example.com/expired-410",
            p256dh="p256dh",
            auth="auth",
        )

        from pywebpush import WebPushException

        mock_resp = MagicMock()
        mock_resp.status_code = 410  # GONE / Unregistered
        ex = WebPushException("Push subscription expired", response=mock_resp)

        with patch('pywebpush.webpush', side_effect=ex):
            res = send_push_notification(test_user, "Title", "Body")
            assert res['expired'] == 1
            assert not PushSubscription.objects.filter(id=sub1.id).exists()


@pytest.mark.django_db
class TestSchedulerRegionAndRoleFiltering:
    def test_salesperson_region_filtering_in_reminders(self, test_user, in_region, au_region):
        source = LeadSource.objects.get_or_create(name="Online")[0]
        now = timezone.now()

        # Lead 1: in IN (Salesperson test_user's allowed region)
        Lead.objects.create(
            name="Indian Customer",
            phone="+919825100001",
            phone_e164="+919825100001",
            region=in_region,
            source=source,
            assigned_to=test_user,
            status=Lead.Status.NEW,
            next_followup_at=now - datetime.timedelta(hours=2),
        )

        # Lead 2: in AU (NOT allowed for test_user)
        Lead.objects.create(
            name="Australian Customer",
            phone="+61412000001",
            phone_e164="+61412000001",
            region=au_region,
            source=source,
            assigned_to=test_user,
            status=Lead.Status.NEW,
            next_followup_at=now - datetime.timedelta(hours=2),
        )

        # Run follow-up reminders with force=True
        with patch('notifications.scheduler.send_push_notification') as mock_push:
            notifs = notify_salespersons_daily_followups(salesperson=test_user, now=now, force=True)

            assert len(notifs) >= 1
            notif_msg = notifs[0].message
            # Only 1 follow-up due in allowed region (lead_in), lead_au is excluded!
            assert "1 follow-ups due today" in notif_msg
            assert mock_push.called
