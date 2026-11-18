import datetime
import socket
from unittest.mock import patch
import zoneinfo

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult

from leads.models import Lead
from masters.models import LeadSource, Region
from notifications.email_service import (
    _sanitize_error,
    _sanitize_header,
    render_base_email,
    run_smtp_diagnostics,
    send_daily_morning_digest,
    send_email_with_retry,
    send_lead_assigned_notification,
    send_password_reset_email,
    send_survey_reminder,
    send_test_email,
)
from notifications.models import EmailLog, NotificationPreference
from surveys.models import Survey

User = get_user_model()


@pytest.fixture
def auth_users(db):
    in_reg, _ = Region.objects.get_or_create(
        code='IN',
        defaults={'name': 'India', 'currency': 'INR', 'currency_symbol': '₹', 'default_timezone': 'Asia/Kolkata'},
    )
    au_reg, _ = Region.objects.get_or_create(
        code='AU',
        defaults={'name': 'Australia', 'currency': 'AUD', 'currency_symbol': '$', 'default_timezone': 'Australia/Sydney'},
    )

    sales_in = User.objects.create_user(
        username='sales_in_user',
        email='sales_in@example.com',
        password='Password123!',
        role='salesperson',
        default_timezone='Asia/Kolkata',
    )
    sales_in.allowed_regions.set([in_reg])

    sales_au = User.objects.create_user(
        username='sales_au_user',
        email='sales_au@example.com',
        password='Password123!',
        role='salesperson',
        default_timezone='Australia/Sydney',
        default_region=au_reg,
    )
    sales_au.allowed_regions.set([au_reg])

    surveyor = User.objects.create_user(
        username='surveyor_user',
        email='surveyor@example.com',
        password='Password123!',
        role='surveyor',
        default_timezone='Asia/Kolkata',
    )
    surveyor.allowed_regions.set([in_reg])

    admin = User.objects.create_user(
        username='admin_test_user',
        email='admin@example.com',
        password='Password123!',
        role='admin',
        is_staff=True,
    )

    return {
        'sales_in': sales_in,
        'sales_au': sales_au,
        'surveyor': surveyor,
        'admin': admin,
        'in_reg': in_reg,
        'au_reg': au_reg,
    }


@pytest.mark.django_db
class TestEmailUnitLocmem:
    """Unit tests for email templates, regional localization, compliance rules, and sanitization."""

    @pytest.fixture(autouse=True)
    def setup_locmem_backend(self, settings):
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


    def test_daily_morning_digest_in_and_au_localization(self, auth_users):
        mail.outbox.clear()
        sales_in = auth_users['sales_in']
        sales_au = auth_users['sales_au']

        # Create leads for IN and AU
        in_lead = Lead.objects.create(
            name="Rahul Sharma",
            phone="9876543210",
            region=auth_users['in_reg'],
            timezone='Asia/Kolkata',
            assigned_to=sales_in,
            next_followup_at=timezone.now(),
            next_action="Review Solar Subsidy",
        )
        au_lead = Lead.objects.create(
            name="Liam O'Connor",
            phone="0412345678",
            region=auth_users['au_reg'],
            timezone='Australia/Sydney',
            assigned_to=sales_au,
            next_followup_at=timezone.now(),
            next_action="Discuss CEC STC Rebate",
        )

        # 1. Test IN Salesperson Digest
        log_in = send_daily_morning_digest(sales_in, due_today_leads=[in_lead], overdue_leads=[])
        assert log_in.status == EmailLog.Status.SENT
        assert len(mail.outbox) == 1
        msg_in = mail.outbox[0]
        assert "Rahul Sharma" in msg_in.body
        assert "IST" in msg_in.body or "Asia/Kolkata" in msg_in.body
        assert "Solar CRM: Daily Follow-up Digest" in msg_in.subject

        # 2. Test AU Salesperson Digest (Australian English spelling)
        mail.outbox.clear()
        log_au = send_daily_morning_digest(sales_au, due_today_leads=[au_lead], overdue_leads=[])
        assert log_au.status == EmailLog.Status.SENT
        assert len(mail.outbox) == 1
        msg_au = mail.outbox[0]
        assert "Liam O&#39;Connor" in msg_au.alternatives[0][0] or "Liam O'Connor" in msg_au.body
        assert "prioritise" in msg_au.alternatives[0][0]
        assert "organised" in msg_au.alternatives[0][0]
        assert "AEDT" in msg_au.body or "AEST" in msg_au.body or "Australia/Sydney" in msg_au.body

    def test_survey_reminder_email(self, auth_users):
        mail.outbox.clear()
        surveyor = auth_users['surveyor']
        sales_in = auth_users['sales_in']
        lead = Lead.objects.create(
            name="Pooja Patel",
            phone="9123456780",
            region=auth_users['in_reg'],
            city="Ahmedabad",
            assigned_to=sales_in,
        )
        survey = Survey.objects.create(
            lead=lead,
            surveyor=surveyor,
            scheduled_at=timezone.now() + datetime.timedelta(days=1),
            status=Survey.Status.BOOKED,
        )

        log = send_survey_reminder(survey, surveyor, role_label="surveyor")
        assert log.status == EmailLog.Status.SENT
        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert "Pooja Patel" in msg.subject
        assert "Ahmedabad" in msg.alternatives[0][0]
        assert "surveyor" in msg.body

    def test_lead_assigned_email(self, auth_users):
        mail.outbox.clear()
        sales_in = auth_users['sales_in']
        source, _ = LeadSource.objects.get_or_create(name='Google Ads')
        lead = Lead.objects.create(
            name="Vikram Mehta",
            phone="9876500000",
            region=auth_users['in_reg'],
            city="Jaipur",
            source=source,
            assigned_to=sales_in,
            next_followup_at=timezone.now() + datetime.timedelta(hours=2),
        )

        log = send_lead_assigned_notification(lead, sales_in)
        assert log.status == EmailLog.Status.SENT
        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert "Vikram Mehta" in msg.subject
        assert "Jaipur" in msg.body
        assert "Google Ads" in msg.body

    def test_user_notification_preference_honored(self, auth_users):
        mail.outbox.clear()
        sales_in = auth_users['sales_in']
        pref, _ = NotificationPreference.objects.get_or_create(user=sales_in)
        pref.email_enabled = False
        pref.save()

        lead = Lead.objects.create(
            name="Ignored Lead",
            phone="9999999999",
            region=auth_users['in_reg'],
            assigned_to=sales_in,
        )

        # Attempt to send digest
        log = send_daily_morning_digest(sales_in, due_today_leads=[lead], overdue_leads=[])
        assert log.status == EmailLog.Status.SKIPPED
        assert "disabled" in log.error.lower()
        assert len(mail.outbox) == 0

        # Attempt to send lead assigned notification
        log_assign = send_lead_assigned_notification(lead, sales_in)
        assert log_assign.status == EmailLog.Status.SKIPPED
        assert len(mail.outbox) == 0

    def test_compliance_guardrails_do_not_contact_and_opt_out(self, auth_users):
        lead_dnc = Lead.objects.create(
            name="DNC Customer",
            phone="9888877777",
            do_not_contact=True,
            region=auth_users['in_reg'],
        )
        assert lead_dnc.do_not_contact is True

        lead_opt = Lead.objects.create(
            name="Opted Out Customer",
            phone="9888866666",
            opt_out_email=True,
            region=auth_users['in_reg'],
        )
        assert lead_opt.opt_out_email is True

    def test_header_injection_prevention(self):
        # Attempt newline injection in subject
        with pytest.raises(ValueError, match="Header injection"):
            _sanitize_header("Subject line\nBcc: hacker@example.com")

        with pytest.raises(ValueError, match="Header injection"):
            _sanitize_header("user@example.com\r\nSubject: Injected")

        # Test safe header passes cleanly
        assert _sanitize_header("Solar CRM: Clean Subject") == "Solar CRM: Clean Subject"

    def test_html_escaping_in_templates(self):
        malicious_input = "<script>alert('pwned')</script> & <b>Bold</b>"
        html_out = render_base_email(
            content_html=f"<p>{malicious_input}</p>",
            title="<script>bad</script>",
            company_name="Solar & Co <test>",
        )
        # Content must have escaped tags in title and company_name
        assert "<script>bad</script>" not in html_out
        assert "&lt;script&gt;bad&lt;/script&gt;" in html_out
        assert "Solar &amp; Co &lt;test&gt;" in html_out

    def test_password_reset_token_expiration_and_single_use(self, client, auth_users):
        mail.outbox.clear()
        sales_in = auth_users['sales_in']

        # 1. Request password reset
        resp = client.post('/api/auth/password-reset/', {'email': sales_in.email}, content_type='application/json')
        assert resp.status_code == 200
        assert len(mail.outbox) == 1

        reset_email = mail.outbox[0]
        assert "Reset Your Password" in reset_email.subject
        assert "reset-password?uid=" in reset_email.body

        uid = urlsafe_base64_encode(force_bytes(sales_in.pk))
        token = default_token_generator.make_token(sales_in)

        # 2. Confirm valid reset token
        confirm_resp = client.post(
            '/api/auth/password-reset/confirm/',
            {'uid': uid, 'token': token, 'new_password': 'BrandNewPassword123!'},
            content_type='application/json',
        )
        assert confirm_resp.status_code == 200

        # 3. Verify single-use: token is now invalid because password hash changed
        reused_resp = client.post(
            '/api/auth/password-reset/confirm/',
            {'uid': uid, 'token': token, 'new_password': 'AnotherPassword123!'},
            content_type='application/json',
        )
        assert reused_resp.status_code == 400
        assert "invalid or expired" in reused_resp.data['error'].lower()

    def test_password_reset_timeout_configured_to_1_hour(self):
        assert getattr(settings, 'PASSWORD_RESET_TIMEOUT', None) == 3600

    def test_secret_scrubbing_in_error_logs(self):
        secret_pw = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        if secret_pw:
            raw_err = f"Failed to authenticate using password={secret_pw} on smtp.gmail.com"
            sanitized = _sanitize_error(raw_err)
            assert secret_pw not in sanitized
            assert "********" in sanitized


class FakeAuthenticator:
    def __call__(self, server, session, envelope, mechanism, auth_data):
        if auth_data.login == b'solar_user' and auth_data.password == b'valid_smtp_pass':
            return AuthResult(success=True)
        return AuthResult(success=False, handled=True)


class TestFakeSmtpIntegration:
    """Integration test suite executing SMTP commands against a local in-process aiosmtpd server."""

    def test_fake_smtp_plain_auth_failure_and_timeout(self):
        # 1. Find a free ephemeral local port
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        temp_sock.bind(('127.0.0.1', 0))
        fake_port = temp_sock.getsockname()[1]
        temp_sock.close()

        # 2. Launch in-process aiosmtpd server
        controller = Controller(
            None,
            hostname='127.0.0.1',
            port=fake_port,
            authenticator=FakeAuthenticator(),
            auth_require_tls=False,
        )
        controller.start()

        try:
            # Test Successful SMTP handshake & authentication
            with override_settings(
                EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
                EMAIL_HOST='127.0.0.1',
                EMAIL_PORT=fake_port,
                EMAIL_USE_TLS=False,
                EMAIL_USE_SSL=False,
                EMAIL_HOST_USER='solar_user',
                EMAIL_HOST_PASSWORD='valid_smtp_pass',
                EMAIL_TIMEOUT=5,
            ):
                diag = run_smtp_diagnostics()
                assert diag["overall_status"] == "pass"
                step_names = [s["name"] for s in diag["steps"]]
                assert "TCP Connection" in step_names
                assert "EHLO Handshake" in step_names
                assert "Authentication" in step_names
                auth_step = next(s for s in diag["steps"] if s["name"] == "Authentication")
                assert auth_step["status"] == "pass"

            # Test Authentication Failure with incorrect password
            with override_settings(
                EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
                EMAIL_HOST='127.0.0.1',
                EMAIL_PORT=fake_port,
                EMAIL_USE_TLS=False,
                EMAIL_USE_SSL=False,
                EMAIL_HOST_USER='solar_user',
                EMAIL_HOST_PASSWORD='WRONG_PASSWORD_XYZ',
                EMAIL_TIMEOUT=5,
            ):
                diag_fail = run_smtp_diagnostics()
                assert diag_fail["overall_status"] == "fail"
                auth_step = next(s for s in diag_fail["steps"] if s["name"] == "Authentication")
                assert auth_step["status"] == "fail"
                assert "Authentication failed" in auth_step["message"] or "Login error" in auth_step["message"]

        finally:
            controller.stop()

        # Test Timeout / Connection Refused on non-listening port
        with override_settings(
            EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
            EMAIL_HOST='127.0.0.1',
            EMAIL_PORT=fake_port,  # Controller stopped, port is now dead
            EMAIL_USE_TLS=False,
            EMAIL_USE_SSL=False,
            EMAIL_HOST_USER='',
            EMAIL_HOST_PASSWORD='',
            EMAIL_TIMEOUT=2,
        ):
            diag_dead = run_smtp_diagnostics()
            assert diag_dead["overall_status"] == "fail"
            conn_step = next(s for s in diag_dead["steps"] if s["name"] == "TCP Connection")
            assert conn_step["status"] == "fail"
            assert "Connection refused" in conn_step["message"] or "timed out" in conn_step["message"]


@pytest.mark.django_db
class TestEmailAdminAndCommand:
    """Verifies the check_email command and admin endpoint."""

    def test_check_email_management_command(self, capsys):
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            call_command('check_email', to='test@example.com')
            captured = capsys.readouterr()
            assert "Solar CRM Email (SMTP) Diagnostics" in captured.out
            assert "Config Validation" in captured.out
            assert "Send Test Email" in captured.out

    def test_admin_email_settings_endpoint(self, client, auth_users):
        admin = auth_users['admin']
        sales = auth_users['sales_in']

        # Salesperson cannot access email settings (403)
        client.force_login(sales)
        resp_sales = client.get('/api/notifications/email-settings/')
        assert resp_sales.status_code == 403

        # Admin can access email settings (200)
        client.force_login(admin)
        resp_admin = client.get('/api/notifications/email-settings/')
        assert resp_admin.status_code == 200
        assert 'settings' in resp_admin.data
        assert 'diagnostics' in resp_admin.data
        assert 'logs' in resp_admin.data
        assert 'host_password_masked' in resp_admin.data['settings']
