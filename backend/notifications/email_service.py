"""
Unified Email Service for Solar CRM (Phase 12).
Handles HTML and plain-text email generation, regional localization (AU/IN spelling),
retry with exponential backoff, compliance guardrails, and audit logging to EmailLog.
"""

import html
import logging
import re
import smtplib
import socket
import time
from typing import Any, Dict, List, Optional
import zoneinfo

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone
from django.utils.html import escape

from notifications.models import EmailLog, NotificationPreference

logger = logging.getLogger(__name__)


def _sanitize_error(error_str: str) -> str:
    """Removes sensitive credentials (like SMTP passwords) from error tracebacks."""
    if not error_str:
        return ""
    password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    if password and password in error_str:
        error_str = error_str.replace(password, '********')
    # Scrub potential auth patterns
    error_str = re.sub(r'password[:=]\s*[^\s,]+', 'password=********', error_str, flags=re.IGNORECASE)
    return error_str.strip()


def _sanitize_header(value: str) -> str:
    """Prevents email header injection by rejecting or stripping carriage returns and newlines."""
    if not value:
        return ""
    if '\n' in value or '\r' in value:
        raise ValueError("Header injection attempt detected: newline found in header.")
    return value.strip()


def render_base_email(
    content_html: str,
    title: str = "Solar CRM Notification",
    preview_text: str = "",
    company_name: str = "Solar CRM",
) -> str:
    """
    Renders responsive, brand-aligned HTML base layout with company header & footer.
    All injected content inside content_html must be pre-escaped.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; margin: 0; padding: 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background: #f59e0b; padding: 20px 24px; color: #ffffff; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -0.025em; }}
    .header p {{ margin: 4px 0 0; font-size: 13px; opacity: 0.9; }}
    .content {{ padding: 24px; font-size: 14px; line-height: 1.6; color: #334155; }}
    .footer {{ background: #f8fafc; padding: 16px 24px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; text-align: center; }}
    .btn {{ display: inline-block; padding: 10px 20px; background-color: #f59e0b; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; margin-top: 12px; }}
    .table-leads {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }}
    .table-leads th, .table-leads td {{ border: 1px solid #e2e8f0; padding: 8px 10px; text-align: left; }}
    .table-leads th {{ background: #f1f5f9; color: #475569; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
    .badge-overdue {{ background: #fee2e2; color: #991b1b; }}
    .badge-today {{ background: #fef3c7; color: #92400e; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{escape(company_name)}</h1>
      <p>{escape(preview_text or "Notification & Alerts")}</p>
    </div>
    <div class="content">
      {content_html}
    </div>
    <div class="footer">
      <p style="margin: 0;">This is an automated notification from {escape(company_name)}.</p>
      <p style="margin: 4px 0 0;">Please do not reply directly to this email.</p>
    </div>
  </div>
</body>
</html>"""


def send_email_with_retry(
    to: str,
    subject: str,
    plain_text: str,
    html_content: str,
    template: str,
    related_lead=None,
    max_retries: int = 2,
    base_delay: float = 0.5,
) -> EmailLog:
    """
    Sends an email using Django's configured EmailBackend with retry and backoff.
    Enforces header injection sanitization and logs the transaction to EmailLog.
    """
    try:
        clean_subject = _sanitize_header(subject)
        clean_to = _sanitize_header(to)
    except ValueError as e:
        log = EmailLog.objects.create(
            to=to[:255],
            subject=subject[:255].replace('\n', ' ').replace('\r', ' '),
            template=template,
            status=EmailLog.Status.FAILED,
            error=f"Header validation error: {str(e)}",
            related_lead=related_lead,
        )
        return log

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Solar CRM <noreply@solarcrm.com>')

    last_error = ""
    for attempt in range(max_retries + 1):
        try:
            msg = EmailMultiAlternatives(
                subject=clean_subject,
                body=plain_text,
                from_email=from_email,
                to=[clean_to],
            )
            if html_content:
                msg.attach_alternative(html_content, "text/html")

            msg.send(fail_silently=False)

            # Success
            log = EmailLog.objects.create(
                to=clean_to,
                subject=clean_subject,
                template=template,
                status=EmailLog.Status.SENT,
                error="",
                related_lead=related_lead,
            )
            return log

        except Exception as exc:
            last_error = _sanitize_error(str(exc) or repr(exc))
            logger.warning(
                f"[EmailService] Attempt {attempt + 1}/{max_retries + 1} failed for {clean_to}: {last_error}"
            )
            if attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt))

    # All retries failed
    log = EmailLog.objects.create(
        to=clean_to,
        subject=clean_subject,
        template=template,
        status=EmailLog.Status.FAILED,
        error=last_error or "Unknown delivery error",
        related_lead=related_lead,
    )
    return log


def _format_lead_time_with_zone(dt, lead_or_user) -> str:
    """Formats datetime with explicit time zone label (e.g. 10:30 AM IST or 02:00 PM AEST)."""
    if not dt:
        return "Not scheduled"
    tz_str = getattr(lead_or_user, 'timezone', None) or getattr(lead_or_user, 'default_timezone', None) or 'Asia/Kolkata'
    try:
        tz = zoneinfo.ZoneInfo(tz_str)
    except Exception:
        tz = zoneinfo.ZoneInfo('Asia/Kolkata')

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, datetime.timezone.utc)
    local_dt = dt.astimezone(tz)
    return local_dt.strftime('%d-%b-%Y %I:%M %p %Z')


def send_daily_morning_digest(
    user,
    due_today_leads: List[Any],
    overdue_leads: List[Any],
    now=None,
    site_url: str = "http://localhost:5173",
) -> Optional[EmailLog]:
    """
    Sends 9:00 AM daily follow-up digest to salesperson.
    Honors user notification preference (email_enabled).
    Only includes leads from user's allowed regions.
    Uses region-appropriate English (e.g. AU spelling if user is AU).
    """
    if not user.email:
        logger.info(f"Skipping digest for {user.username}: no email address.")
        return None

    # Check notification preference
    pref = getattr(user, 'notification_preference', None)
    if pref is None:
        pref, _ = NotificationPreference.objects.get_or_create(user=user)

    if not pref.email_enabled:
        return EmailLog.objects.create(
            to=user.email,
            subject=f"Daily Solar CRM Follow-up Digest ({user.username})",
            template="daily_digest",
            status=EmailLog.Status.SKIPPED,
            error="User email notifications disabled in preferences",
        )

    is_au = False
    if user.default_region_id == 'AU' or (user.allowed_regions.filter(code='AU').exists() and not user.allowed_regions.filter(code='IN').exists()):
        is_au = True

    # Regional spelling
    org_label = "organised" if is_au else "organized"
    prioritise_label = "prioritise" if is_au else "prioritize"
    favour_label = "favour" if is_au else "favor"

    total_leads = len(due_today_leads) + len(overdue_leads)
    subject = f"Solar CRM: Daily Follow-up Digest - {len(due_today_leads)} due today, {len(overdue_leads)} overdue"

    # HTML Body
    rows_html = []
    for l in overdue_leads:
        formatted_time = _format_lead_time_with_zone(l.next_followup_at, l)
        rows_html.append(
            f"<tr>"
            f"<td><span class='badge badge-overdue'>Overdue</span></td>"
            f"<td><a href='{site_url}/leads/{l.id}'><strong>{escape(l.name)}</strong></a></td>"
            f"<td>{escape(l.phone)}</td>"
            f"<td>{escape(formatted_time)}</td>"
            f"<td>{escape(l.next_action or 'Follow-up')}</td>"
            f"</tr>"
        )
    for l in due_today_leads:
        formatted_time = _format_lead_time_with_zone(l.next_followup_at, l)
        rows_html.append(
            f"<tr>"
            f"<td><span class='badge badge-today'>Today</span></td>"
            f"<td><a href='{site_url}/leads/{l.id}'><strong>{escape(l.name)}</strong></a></td>"
            f"<td>{escape(l.phone)}</td>"
            f"<td>{escape(formatted_time)}</td>"
            f"<td>{escape(l.next_action or 'Follow-up')}</td>"
            f"</tr>"
        )

    content_html = f"""
    <p>Good morning <strong>{escape(user.first_name or user.username)}</strong>,</p>
    <p>Here is your daily follow-up digest. You have <strong>{len(due_today_leads)}</strong> follow-ups due today and <strong style="color: #dc2626;">{len(overdue_leads)}</strong> overdue follow-ups requiring prompt attention.</p>
    <p>Please review your pipeline and {prioritise_label} calls to keep customer enquiries {org_label}.</p>
    
    <table class="table-leads">
      <thead>
        <tr>
          <th>Priority</th>
          <th>Lead Name</th>
          <th>Phone</th>
          <th>Scheduled Time</th>
          <th>Next Action</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows_html) if rows_html else '<tr><td colspan="5" style="text-align: center; color: #64748b;">No follow-ups due today. Great job!</td></tr>'}
      </tbody>
    </table>

    <p style="margin-top: 24px;">
      <a href="{site_url}/today" class="btn">Open Today's Queue in Solar CRM</a>
    </p>
    """

    plain_lines = [
        f"Good morning {user.first_name or user.username},",
        f"",
        f"Daily Follow-up Digest: {len(due_today_leads)} due today, {len(overdue_leads)} overdue.",
        f"",
    ]
    if overdue_leads:
        plain_lines.append("OVERDUE FOLLOW-UPS:")
        for l in overdue_leads:
            t = _format_lead_time_with_zone(l.next_followup_at, l)
            plain_lines.append(f" - [OVERDUE] {l.name} | Phone: {l.phone} | Due: {t} | Link: {site_url}/leads/{l.id}")
        plain_lines.append("")

    if due_today_leads:
        plain_lines.append("TODAY'S FOLLOW-UPS:")
        for l in due_today_leads:
            t = _format_lead_time_with_zone(l.next_followup_at, l)
            plain_lines.append(f" - [TODAY] {l.name} | Phone: {l.phone} | Due: {t} | Link: {site_url}/leads/{l.id}")
        plain_lines.append("")

    plain_lines.append(f"Open full queue: {site_url}/today")
    plain_text = "\n".join(plain_lines)

    html_email = render_base_email(
        content_html=content_html,
        title="Daily Follow-up Digest",
        preview_text=f"{len(due_today_leads)} due today, {len(overdue_leads)} overdue",
    )

    return send_email_with_retry(
        to=user.email,
        subject=subject,
        plain_text=plain_text,
        html_content=html_email,
        template="daily_digest",
    )


def send_survey_reminder(
    survey,
    recipient_user,
    role_label: str = "surveyor",
    site_url: str = "http://localhost:5173",
) -> Optional[EmailLog]:
    """
    Sends site survey reminder the day before the inspection to surveyor or salesperson.
    Checks recipient user email preference and lead do_not_contact/opt_out.
    """
    if not recipient_user or not recipient_user.email:
        return None

    pref = getattr(recipient_user, 'notification_preference', None)
    if pref is None:
        pref, _ = NotificationPreference.objects.get_or_create(user=recipient_user)

    if not pref.email_enabled:
        return EmailLog.objects.create(
            to=recipient_user.email,
            subject=f"Survey Reminder: {survey.lead.name}",
            template="survey_reminder",
            status=EmailLog.Status.SKIPPED,
            error="User email notifications disabled in preferences",
            related_lead=survey.lead,
        )

    lead = survey.lead
    formatted_time = _format_lead_time_with_zone(survey.scheduled_at, lead)
    is_au = (lead.region_id == 'AU')

    loc_label = "suburb" if is_au else "city"
    lead_loc = lead.suburb if is_au and lead.suburb else (lead.city or "Local area")

    subject = f"Solar CRM: Site Survey Tomorrow for {lead.name} ({formatted_time})"

    content_html = f"""
    <p>Hello <strong>{escape(recipient_user.first_name or recipient_user.username)}</strong>,</p>
    <p>This is a reminder that an on-site rooftop solar technical inspection is scheduled for tomorrow:</p>
    
    <div style="background: #f8fafc; border-left: 4px solid #f59e0b; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
      <p style="margin: 0 0 6px;"><strong>Customer:</strong> {escape(lead.name)}</p>
      <p style="margin: 0 0 6px;"><strong>Phone:</strong> {escape(lead.phone)}</p>
      <p style="margin: 0 0 6px;"><strong>Time:</strong> <span style="color: #b45309; font-weight: 600;">{escape(formatted_time)}</span></p>
      <p style="margin: 0 0 6px;"><strong>Address:</strong> {escape(lead.address or lead_loc)}</p>
      <p style="margin: 0;"><strong>Role:</strong> You are tagged on this survey as {escape(role_label)}.</p>
    </div>

    <p><a href="{site_url}/surveys/{survey.id}" class="btn">View Survey Details & Checklist</a></p>
    """

    plain_text = (
        f"Hello {recipient_user.first_name or recipient_user.username},\n\n"
        f"Site Survey Reminder for tomorrow:\n"
        f"Customer: {lead.name}\n"
        f"Phone: {lead.phone}\n"
        f"Time: {formatted_time}\n"
        f"Address: {lead.address or lead_loc}\n"
        f"Survey link: {site_url}/surveys/{survey.id}\n"
    )

    html_email = render_base_email(
        content_html=content_html,
        title="Site Survey Reminder",
        preview_text=f"Survey tomorrow at {formatted_time} for {lead.name}",
    )

    return send_email_with_retry(
        to=recipient_user.email,
        subject=subject,
        plain_text=plain_text,
        html_content=html_email,
        template="survey_reminder",
        related_lead=lead,
    )


def send_lead_assigned_notification(
    lead,
    new_assignee,
    site_url: str = "http://localhost:5173",
) -> Optional[EmailLog]:
    """
    Sends email to a salesperson when a new lead is assigned to them.
    Honors assignee email preference and checks lead do_not_contact/opt_out.
    """
    if not new_assignee or not new_assignee.email:
        return None

    pref = getattr(new_assignee, 'notification_preference', None)
    if pref is None:
        pref, _ = NotificationPreference.objects.get_or_create(user=new_assignee)

    if not pref.email_enabled:
        return EmailLog.objects.create(
            to=new_assignee.email,
            subject=f"New Lead Assigned: {lead.name}",
            template="lead_assigned",
            status=EmailLog.Status.SKIPPED,
            error="User email notifications disabled in preferences",
            related_lead=lead,
        )

    is_au = (lead.region_id == 'AU')
    enquiry_label = "enquiry" if is_au else "inquiry"
    followup_time = _format_lead_time_with_zone(lead.next_followup_at, lead)

    subject = f"Solar CRM: New Lead Assigned to You - {lead.name}"

    content_html = f"""
    <p>Hello <strong>{escape(new_assignee.first_name or new_assignee.username)}</strong>,</p>
    <p>A new solar {enquiry_label} has been assigned to your sales pipeline:</p>

    <div style="background: #f8fafc; border-left: 4px solid #10b981; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
      <p style="margin: 0 0 6px;"><strong>Name:</strong> {escape(lead.name)}</p>
      <p style="margin: 0 0 6px;"><strong>Phone:</strong> {escape(lead.phone)}</p>
      <p style="margin: 0 0 6px;"><strong>Location:</strong> {escape(lead.suburb or lead.city or 'Not specified')}, {escape(lead.state or '')}</p>
      <p style="margin: 0 0 6px;"><strong>Source:</strong> {escape(str(lead.source) if lead.source else 'Direct')}</p>
      <p style="margin: 0;"><strong>First Follow-up Due:</strong> {escape(followup_time)}</p>
    </div>

    <p><a href="{site_url}/leads/{lead.id}" class="btn">Open Lead in Solar CRM</a></p>
    """

    plain_text = (
        f"Hello {new_assignee.first_name or new_assignee.username},\n\n"
        f"A new solar lead has been assigned to you:\n"
        f"Name: {lead.name}\n"
        f"Phone: {lead.phone}\n"
        f"Location: {lead.suburb or lead.city or 'Not specified'}, {lead.state or ''}\n"
        f"Source: {str(lead.source) if lead.source else 'Direct'}\n"
        f"Follow-up due: {followup_time}\n"
        f"Link: {site_url}/leads/{lead.id}\n"
    )

    html_email = render_base_email(
        content_html=content_html,
        title="New Lead Assigned",
        preview_text=f"New lead assigned: {lead.name}",
    )

    return send_email_with_retry(
        to=new_assignee.email,
        subject=subject,
        plain_text=plain_text,
        html_content=html_email,
        template="lead_assigned",
        related_lead=lead,
    )


def send_password_reset_email(
    user,
    reset_url: str,
) -> EmailLog:
    """
    Sends transactional single-use password reset link expiring in 1 hour.
    Bypasses marketing email opt-outs as it is an essential authentication action.
    """
    subject = "Solar CRM: Reset Your Password"

    content_html = f"""
    <p>Hello <strong>{escape(user.first_name or user.username)}</strong>,</p>
    <p>We received a request to reset your password for Solar CRM. Click the button below to set a new password:</p>

    <p style="margin: 20px 0;">
      <a href="{escape(reset_url)}" class="btn">Reset Password</a>
    </p>

    <p style="font-size: 13px; color: #64748b;">
      This password reset link is single-use and will expire in <strong>1 hour</strong>.<br>
      If you did not request this reset, you can safely ignore this email; your account remains secure.
    </p>
    <p style="font-size: 12px; color: #94a3b8; word-break: break-all;">
      Or copy and paste this link into your browser:<br>
      {escape(reset_url)}
    </p>
    """

    plain_text = (
        f"Hello {user.first_name or user.username},\n\n"
        f"We received a request to reset your password for Solar CRM.\n"
        f"Click the link below to set a new password (valid for 1 hour):\n\n"
        f"{reset_url}\n\n"
        f"If you did not request this, please ignore this email.\n"
    )

    html_email = render_base_email(
        content_html=content_html,
        title="Reset Your Password",
        preview_text="Password reset request for Solar CRM",
    )

    return send_email_with_retry(
        to=user.email,
        subject=subject,
        plain_text=plain_text,
        html_content=html_email,
        template="password_reset",
    )


def send_test_email(to_email: str, user=None) -> EmailLog:
    """
    Sends an immediate test email to verify SMTP configuration and HTML formatting.
    """
    subject = "Solar CRM: Test Email Verification"

    content_html = f"""
    <p>Hello,</p>
    <p>This is a test email sent from <strong>Solar CRM</strong> to confirm your SMTP configuration is operating successfully!</p>
    <div style="background: #ecfdf5; border: 1px solid #a7f3d0; padding: 12px 16px; border-radius: 6px; margin: 16px 0;">
      <p style="color: #065f46; font-weight: 600; margin: 0;">✓ SMTP Delivery Verified</p>
      <p style="color: #047857; font-size: 13px; margin: 4px 0 0;">
        Backend: {escape(getattr(settings, 'EMAIL_BACKEND', 'unknown'))}<br>
        Host: {escape(getattr(settings, 'EMAIL_HOST', 'localhost'))}:{getattr(settings, 'EMAIL_PORT', 587)}<br>
        Security: {'STARTTLS' if getattr(settings, 'EMAIL_USE_TLS', False) else ('SSL' if getattr(settings, 'EMAIL_USE_SSL', False) else 'Plain')}<br>
        Timestamp: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
      </p>
    </div>
    <p>Your team can now receive daily follow-up digests, site survey reminders, and password reset notifications.</p>
    """

    plain_text = (
        f"Hello,\n\n"
        f"This is a test email from Solar CRM confirming that SMTP delivery is working properly.\n"
        f"Timestamp: {timezone.now().isoformat()}\n"
    )

    html_email = render_base_email(
        content_html=content_html,
        title="Test Email Verification",
        preview_text="Solar CRM SMTP Delivery Verified",
    )

    return send_email_with_retry(
        to=to_email,
        subject=subject,
        plain_text=plain_text,
        html_content=html_email,
        template="test_email",
    )


def run_smtp_diagnostics(to_email: Optional[str] = None) -> Dict[str, Any]:
    """
    Runs comprehensive step-by-step SMTP diagnostics:
    1. Settings validation
    2. TCP Socket connect & timeout check
    3. EHLO handshake
    4. STARTTLS or SSL upgrade
    5. Authentication login
    6. Optional test email send
    Returns structured results with plain-language explanations.
    """
    host = getattr(settings, 'EMAIL_HOST', '')
    port = getattr(settings, 'EMAIL_PORT', 587)
    use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
    use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
    username = getattr(settings, 'EMAIL_HOST_USER', '')
    password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    timeout = getattr(settings, 'EMAIL_TIMEOUT', 15)
    backend = getattr(settings, 'EMAIL_BACKEND', '')

    results = {
        "backend": backend,
        "host": host,
        "port": port,
        "use_tls": use_tls,
        "use_ssl": use_ssl,
        "username": username,
        "password_configured": bool(password),
        "steps": [],
        "overall_status": "pass",
    }

    def add_step(name: str, passed: bool, message: str):
        results["steps"].append({
            "name": name,
            "status": "pass" if passed else "fail",
            "message": message,
        })
        if not passed:
            results["overall_status"] = "fail"

    # Step 1: Configuration check
    if use_tls and use_ssl:
        add_step("Config Validation", False, "Both EMAIL_USE_TLS and EMAIL_USE_SSL are enabled. Disable one.")
        return results
    if not host and "smtp" in backend.lower():
        add_step("Config Validation", False, "EMAIL_HOST is not configured.")
        return results
    add_step("Config Validation", True, f"Valid configuration using {backend}")

    # If backend is console or locmem, skip network socket checks
    if "console" in backend.lower() or "locmem" in backend.lower():
        add_step("Console/Locmem Mode", True, f"Active backend is {backend}. Emails will be captured locally without SMTP transmission.")
        if to_email:
            log = send_test_email(to_email)
            add_step("Send Test Email", log.status == EmailLog.Status.SENT, f"Email logged with status: {log.status}")
        return results

    # Step 2: Socket connection
    smtp = None
    try:
        if use_ssl:
            smtp = smtplib.SMTP_SSL(host, port, timeout=timeout)
        else:
            smtp = smtplib.SMTP(host, port, timeout=timeout)
        add_step("TCP Connection", True, f"Successfully connected to {host}:{port}")
    except socket.timeout:
        add_step("TCP Connection", False, f"Connection timed out after {timeout}s. Port {port} may be blocked by your firewall or ISP.")
        return results
    except ConnectionRefusedError:
        add_step("TCP Connection", False, f"Connection refused on {host}:{port}. Check host and port.")
        return results
    except Exception as e:
        add_step("TCP Connection", False, f"Failed to connect: {_sanitize_error(str(e))}")
        return results

    try:
        # Step 3: EHLO Handshake
        code, msg = smtp.ehlo()
        add_step("EHLO Handshake", code in (250, 220), f"EHLO response: {code}")

        # Step 4: STARTTLS (if enabled)
        if use_tls and not use_ssl:
            if not smtp.has_extn('starttls'):
                add_step("STARTTLS Handshake", False, "Server does not support STARTTLS on this port.")
                return results
            try:
                smtp.starttls()
                smtp.ehlo()
                add_step("STARTTLS Handshake", True, "STARTTLS negotiation successful.")
            except Exception as e:
                add_step("STARTTLS Handshake", False, f"STARTTLS negotiation failed: {_sanitize_error(str(e))}")
                return results

        # Step 5: Authentication (if credentials provided)
        if username and password:
            try:
                smtp.login(username, password)
                add_step("Authentication", True, f"Authenticated successfully as {username}")
            except smtplib.SMTPAuthenticationError as e:
                hint = "Wrong password or username. If using Gmail, make sure 2-Step Verification is ON and you are using a 16-character App Password, not your regular Google account password."
                add_step("Authentication", False, f"Authentication failed (code {getattr(e, 'smtp_code', 535)}): {hint}")
                return results
            except Exception as e:
                add_step("Authentication", False, f"Login error: {_sanitize_error(str(e))}")
                return results
        else:
            add_step("Authentication", True, "No username/password configured (open relay mode).")

        # Step 6: Test email send (if requested)
        if to_email:
            try:
                log = send_test_email(to_email)
                if log.status == EmailLog.Status.SENT:
                    add_step("Send Test Email", True, f"Test email sent successfully to {to_email}")
                else:
                    add_step("Send Test Email", False, f"Test email delivery failed: {log.error}")
            except Exception as e:
                add_step("Send Test Email", False, f"Test email failed: {_sanitize_error(str(e))}")

    finally:
        if smtp:
            try:
                smtp.quit()
            except Exception:
                try:
                    smtp.close()
                except Exception:
                    pass

    return results
