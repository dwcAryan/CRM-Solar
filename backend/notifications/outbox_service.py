"""
Asynchronous Email Outbox and Delivery Service (Phase 14M).
Features:
- Rate limiting (max 30 emails/minute)
- Idempotency key deduplication
- Exponential backoff on transient errors (60s, 120s, 240s, 480s, max 5 attempts)
- Immediate fast-fail on permanent errors (header injection, malformed email)
- Inlined CSS with premailer for robust email client deliverability
- List-Unsubscribe and Precedence: bulk headers
- Comprehensive audit logging via EmailLog
"""

import datetime
import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models, transaction
from django.utils import timezone

from notifications.models import EmailLog, EmailOutbox
from notifications.email_service import _sanitize_error, _sanitize_header, render_base_email

logger = logging.getLogger(__name__)

try:
    import premailer
    HAS_PREMAILER = True
except ImportError:
    HAS_PREMAILER = False


def inline_css(html_content: str) -> str:
    """Inlines CSS into tags using premailer if available."""
    if not html_content or not HAS_PREMAILER:
        return html_content
    try:
        return premailer.transform(html_content)
    except Exception as exc:
        logger.warning(f"[OutboxService] Premailer inlining warning: {exc}")
        return html_content


def queue_email(
    to: str,
    subject: str,
    template_name: str,
    context_json: Optional[Dict[str, Any]] = None,
    language: str = 'en',
    idempotency_key: Optional[str] = None,
    related_lead=None,
    is_urgent: bool = False,
    plain_text: str = "",
    html_content: str = "",
) -> EmailOutbox:
    """
    Queues an email in the EmailOutbox.
    If idempotency_key is provided and an existing item matches, returns existing item.
    If is_urgent is True, synchronously dispatches immediately.
    """
    if context_json is None:
        context_json = {}

    if plain_text:
        context_json['plain_text'] = plain_text
    if html_content:
        context_json['html_content'] = html_content

    if idempotency_key:
        existing = EmailOutbox.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            logger.info(f"[OutboxService] Idempotent hit for key {idempotency_key}, skipping duplicate queue.")
            return existing

    outbox_item = EmailOutbox.objects.create(
        to=to.strip(),
        subject=subject.strip(),
        template_name=template_name,
        context_json=context_json,
        language=language,
        idempotency_key=idempotency_key,
        related_lead=related_lead,
        status=EmailOutbox.Status.PENDING,
        attempts=0,
        next_attempt_at=timezone.now(),
    )

    if is_urgent:
        dispatch_outbox_item(outbox_item)

    return outbox_item


def render_outbox_content(item: EmailOutbox) -> tuple[str, str]:
    """
    Renders plain text and HTML for an outbox item based on template and context.
    Returns (plain_text, html_content).
    """
    ctx = item.context_json or {}
    plain_text = ctx.get('plain_text', '')
    html_content = ctx.get('html_content', '')

    if html_content:
        html_content = inline_css(html_content)
        return plain_text, html_content

    # Default fallback
    body_text = ctx.get('body', plain_text or item.subject)
    html = render_base_email(
        content_html=f"<p>{body_text}</p>",
        title=item.subject,
    )
    return body_text, inline_css(html)


def check_rate_limit(window_seconds: int = 60, max_emails: int = 30) -> bool:
    """Returns True if sending is permitted, False if rate limit window is saturated."""
    since = timezone.now() - datetime.timedelta(seconds=window_seconds)
    recent_count = EmailLog.objects.filter(
        status=EmailLog.Status.SENT,
        created_at__gte=since,
    ).count()
    return recent_count < max_emails


def dispatch_outbox_item(item: EmailOutbox) -> bool:
    """
    Dispatches a single outbox item through Django mail backend.
    Enforces rate limiting, retries transient failures with exponential backoff,
    and fast-fails permanent errors.
    """
    if item.status == EmailOutbox.Status.SENT:
        return True

    # Check rate limit (except for urgent password resets)
    is_urgent = (item.template_name == 'password_reset')
    if not is_urgent and not check_rate_limit(window_seconds=60, max_emails=30):
        logger.warning(f"[OutboxService] Rate limit hit (30/min). Postponing item #{item.id}")
        item.next_attempt_at = timezone.now() + datetime.timedelta(seconds=15)
        item.save(update_fields=['next_attempt_at'])
        return False

    # Validate headers to prevent header injection
    try:
        clean_subject = _sanitize_header(item.subject)
        clean_to = _sanitize_header(item.to)
    except ValueError as val_err:
        error_msg = f"Permanent header validation error: {val_err}"
        item.status = EmailOutbox.Status.FAILED
        item.last_error = error_msg
        item.save(update_fields=['status', 'last_error'])
        EmailLog.objects.create(
            to=item.to[:255],
            subject=item.subject[:255].replace('\n', ' ').replace('\r', ' '),
            template=item.template_name,
            status=EmailLog.Status.FAILED,
            error=error_msg,
            related_lead=item.related_lead,
        )
        return False

    # Render content
    plain_text, html_content = render_outbox_content(item)
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Solar CRM <noreply@solarcrm.com>')

    headers = {}
    if not is_urgent:
        headers['Precedence'] = 'bulk'
        site_url = getattr(settings, 'APP_BASE_URL', 'http://localhost:5173')
        headers['List-Unsubscribe'] = f"<{site_url}/settings/notifications>"

    try:
        msg = EmailMultiAlternatives(
            subject=clean_subject,
            body=plain_text,
            from_email=from_email,
            to=[clean_to],
            headers=headers,
        )
        if html_content:
            msg.attach_alternative(html_content, "text/html")

        msg.send(fail_silently=False)

        # Success
        item.status = EmailOutbox.Status.SENT
        item.sent_at = timezone.now()
        item.last_error = ""
        item.save(update_fields=['status', 'sent_at', 'last_error'])

        EmailLog.objects.create(
            to=clean_to,
            subject=clean_subject,
            template=item.template_name,
            status=EmailLog.Status.SENT,
            error="",
            related_lead=item.related_lead,
        )
        return True

    except Exception as exc:
        err_str = _sanitize_error(str(exc) or repr(exc))
        item.attempts += 1
        item.last_error = err_str

        # Distinguish permanent vs transient errors
        is_permanent = any(kw in err_str.lower() for kw in [
            'syntax error', 'invalid address', 'recipient rejected', 'relay access denied',
            'mailbox unavailable', '550', '551', '553'
        ])

        if is_permanent or item.attempts >= 5:
            item.status = EmailOutbox.Status.FAILED
            EmailLog.objects.create(
                to=clean_to,
                subject=clean_subject,
                template=item.template_name,
                status=EmailLog.Status.FAILED,
                error=err_str,
                related_lead=item.related_lead,
            )
        else:
            # Exponential backoff: 60s, 120s, 240s, 480s
            backoff_sec = 60 * (2 ** (item.attempts - 1))
            item.next_attempt_at = timezone.now() + datetime.timedelta(seconds=backoff_sec)

        item.save(update_fields=['attempts', 'last_error', 'status', 'next_attempt_at'])
        return False


def process_outbox_batch(limit: int = 30) -> int:
    """
    Processes pending outbox items that are ready to be dispatched.
    Returns the count of successfully sent items.
    """
    now = timezone.now()
    pending_items = list(
        EmailOutbox.objects.filter(
            status=EmailOutbox.Status.PENDING,
        ).filter(
            models.Q(next_attempt_at__isnull=True) | models.Q(next_attempt_at__lte=now)
        ).order_by('created_at')[:limit]
    )

    success_count = 0
    for item in pending_items:
        if dispatch_outbox_item(item):
            success_count += 1
    return success_count
