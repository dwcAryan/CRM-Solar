import datetime
import zoneinfo

from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    message = models.TextField()
    message_code = models.CharField(max_length=100, blank=True, default='')
    params = models.JSONField(default=dict, blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self) -> str:
        status_str = "Read" if self.is_read else "Unread"
        return f"[{status_str}] {self.user.username}: {self.message[:40]}"


class NotificationPreference(models.Model):
    """
    Per-user notification delivery channels and quiet hours preferences.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preference',
    )
    in_app_enabled = models.BooleanField(default=True)
    browser_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(default="22:00")
    quiet_hours_end = models.TimeField(default="08:00")

    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self) -> str:
        return f"Preferences for {self.user.username}"

    def is_in_quiet_hours(self, dt_in_user_tz: datetime.datetime | None = None) -> bool:
        """
        Check if given datetime (or now) falls inside the user's quiet hours window.
        Uses the user's default_timezone.
        """
        if not self.quiet_hours_enabled:
            return False

        if dt_in_user_tz is None:
            tz_str = getattr(self.user, 'default_timezone', None) or 'Asia/Kolkata'
            try:
                user_tz = zoneinfo.ZoneInfo(tz_str)
            except Exception:
                user_tz = zoneinfo.ZoneInfo('Asia/Kolkata')
            dt_in_user_tz = timezone.now().astimezone(user_tz)

        current_time = dt_in_user_tz.time()
        start = self.quiet_hours_start
        end = self.quiet_hours_end

        if start <= end:
            return start <= current_time <= end
        else:
            # Overnight range, e.g. 22:00 -> 08:00
            return current_time >= start or current_time <= end


class PushSubscription(models.Model):
    """
    Stores Web Push subscription endpoints and crypto keys for browser push delivery.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    user_agent = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Push Subscription'
        verbose_name_plural = 'Push Subscriptions'

    def __str__(self) -> str:
        return f"PushSub({self.user.username} - {self.endpoint[:30]}...)"


class EmailLog(models.Model):
    """
    Audit log of outgoing system and transactional emails.
    Stores status, template, timestamp, error traces sanitized of credentials,
    and link to optional related customer lead.
    """
    class Status(models.TextChoices):
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'

    to = models.EmailField(max_length=255)
    subject = models.CharField(max_length=255)
    template = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)
    error = models.TextField(blank=True, default='')
    related_lead = models.ForeignKey(
        'leads.Lead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['template']),
        ]
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'

    def __str__(self) -> str:
        return f"[{self.status.upper()}] {self.template} -> {self.to} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

