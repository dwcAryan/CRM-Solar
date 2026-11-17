from django.db import models


class MessageTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    body = models.TextField(help_text="Message text with placeholder variables e.g. {customer_name}, {time}")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Message Template'
        verbose_name_plural = 'Message Templates'

    def __str__(self) -> str:
        return self.name

    def render(self, params: dict) -> str:
        text = self.body
        for k, v in params.items():
            text = text.replace(f"{{{k}}}", str(v))
        return text


class MessageLog(models.Model):
    class Status(models.TextChoices):
        SENT = 'sent', 'Sent'
        BLOCKED = 'blocked', 'Blocked (Do Not Contact)'
        FAILED = 'failed', 'Failed'

    phone = models.CharField(max_length=20)
    lead = models.ForeignKey(
        'leads.Lead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='message_logs',
    )
    template_name = models.CharField(max_length=100, blank=True)
    params = models.JSONField(default=dict, blank=True)
    message_text = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Message Log'
        verbose_name_plural = 'Message Logs'

    def __str__(self) -> str:
        return f"[{self.status}] to {self.phone} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"
