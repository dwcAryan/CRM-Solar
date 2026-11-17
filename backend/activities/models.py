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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'

    def __str__(self) -> str:
        return f"{self.get_type_display()} on {self.lead.name} -> {self.status_after} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
