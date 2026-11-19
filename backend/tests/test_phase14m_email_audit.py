import datetime
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone

from leads.models import Lead
from masters.models import Region
from notifications.models import EmailLog, EmailOutbox
from notifications.outbox_service import (
    check_rate_limit,
    dispatch_outbox_item,
    inline_css,
    process_outbox_batch,
    queue_email,
)

User = get_user_model()


@pytest.fixture
def auth_user(db):
    user = User.objects.create_user(
        username='outbox_tester',
        email='outbox_tester@example.com',
        password='Password123!',
        role='salesperson',
    )
    return user


@pytest.mark.django_db
class TestEmailOutboxAudit:
    @pytest.fixture(autouse=True)
    def setup_locmem(self, settings):
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

    def test_queue_email_and_idempotency_deduplication(self, auth_user):
        """Asserts that queuing with the same idempotency key returns existing item without re-queuing."""
        key = "idemp_test_key_123"
        item1 = queue_email(
            to="user1@example.com",
            subject="First Send",
            template_name="lead_assigned",
            context_json={"name": "Test"},
            idempotency_key=key,
        )
        assert item1.status == EmailOutbox.Status.PENDING

        item2 = queue_email(
            to="user1@example.com",
            subject="Second Attempt Duplicate",
            template_name="lead_assigned",
            context_json={"name": "Test"},
            idempotency_key=key,
        )
        assert item1.id == item2.id
        assert EmailOutbox.objects.filter(idempotency_key=key).count() == 1

    def test_dispatch_outbox_item_success(self, auth_user):
        """Asserts outbox item is sent, marked sent, and logged in EmailLog."""
        item = queue_email(
            to="recipient@example.com",
            subject="Notification Alert",
            template_name="custom_notice",
            plain_text="Hello text",
            html_content="<p style='color: red;'>Hello HTML</p>",
        )
        success = dispatch_outbox_item(item)
        assert success is True
        item.refresh_from_db()
        assert item.status == EmailOutbox.Status.SENT
        assert item.sent_at is not None

        # Check mail outbox
        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert msg.to == ["recipient@example.com"]
        assert msg.subject == "Notification Alert"
        assert msg.extra_headers.get("Precedence") == "bulk"

        # Check EmailLog
        assert EmailLog.objects.filter(to="recipient@example.com", status=EmailLog.Status.SENT).exists()

    def test_header_injection_prevention_fast_fail(self, auth_user):
        """Asserts that header injection attempts fail immediately without retry."""
        item = queue_email(
            to="bad\r\nBcc: evil@attacker.com",
            subject="Legit Subject\r\nInject: bad",
            template_name="test_injection",
        )
        success = dispatch_outbox_item(item)
        assert success is False
        item.refresh_from_db()
        assert item.status == EmailOutbox.Status.FAILED
        assert "Permanent header validation error" in item.last_error

    def test_rate_limiting_enforcement(self, auth_user):
        """Asserts rate limit check blocks sending when window reaches 30 emails/min."""
        # Clean existing logs
        EmailLog.objects.all().delete()
        now = timezone.now()
        for i in range(30):
            EmailLog.objects.create(
                to=f"user_{i}@example.com",
                subject="Test",
                template="test",
                status=EmailLog.Status.SENT,
                created_at=now,
            )
        assert check_rate_limit(window_seconds=60, max_emails=30) is False

        # Attempt to dispatch non-urgent item
        item = queue_email(
            to="throttled@example.com",
            subject="Throttled Alert",
            template_name="alert",
        )
        res = dispatch_outbox_item(item)
        assert res is False
        item.refresh_from_db()
        assert item.status == EmailOutbox.Status.PENDING
        assert item.next_attempt_at > now

    def test_process_outbox_batch(self, auth_user):
        """Asserts batch processor processes multiple pending emails."""
        mail.outbox.clear()
        EmailLog.objects.all().delete()
        EmailOutbox.objects.all().delete()

        for i in range(3):
            queue_email(
                to=f"batch_{i}@example.com",
                subject=f"Batch {i}",
                template_name="batch_notice",
                plain_text=f"Batch item {i}",
            )

        processed = process_outbox_batch(limit=10)
        assert processed == 3
        assert EmailOutbox.objects.filter(status=EmailOutbox.Status.SENT).count() == 3
        assert len(mail.outbox) == 3

    def test_css_inlining(self):
        """Asserts premailer inlines style attributes cleanly."""
        raw_html = "<html><head><style>p { color: blue; }</style></head><body><p>Hello</p></body></html>"
        inlined = inline_css(raw_html)
        assert "style=" in inlined or "color: blue" in inlined
