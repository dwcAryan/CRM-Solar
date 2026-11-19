from django.conf import settings
from django.db import models


class Activity(models.Model):
    class Type(models.TextChoices):
        CALL = 'call', 'Call'
        WHATSAPP = 'whatsapp', 'WhatsApp'
        VISIT = 'visit', 'Visit'
        NOTE = 'note', 'Note'

    lead = models.ForeignKey(
        'leads.Lead',
        on_delete=models.CASCADE,
        related_name='activities',
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    outcome = models.ForeignKey(
        'masters.Outcome',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
    )
    notes = models.TextField(blank=True)
    message_code = models.CharField(max_length=100, blank=True, default='')
    params = models.JSONField(default=dict, blank=True)
    remark = models.CharField(max_length=500, blank=True, default='')
    status_after = models.CharField(max_length=50)
    next_action = models.CharField(max_length=255, blank=True)
    next_followup_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_activities',
    )
    admin_correction_note = models.TextField(blank=True, default='')
    correction_added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='corrected_activities',
    )
    correction_added_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.lead_id:
            from leads.models import Lead
            Lead.objects.filter(pk=self.lead_id).update(last_activity_at=self.created_at)

    def __str__(self) -> str:
        return f"{self.get_type_display()} on {self.lead.name} -> {self.status_after} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
