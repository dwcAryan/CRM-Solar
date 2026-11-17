from django.conf import settings
from django.db import models


class Survey(models.Model):
    class Status(models.TextChoices):
        BOOKED = 'booked', 'Booked'
        RESCHEDULED = 'rescheduled', 'Rescheduled'
        MISSED = 'missed', 'Missed'
        DONE = 'done', 'Done'
        CANCELLED = 'cancelled', 'Cancelled'

    lead = models.ForeignKey(
        'leads.Lead',
        on_delete=models.CASCADE,
        related_name='surveys',
    )
    scheduled_at = models.DateTimeField()
    surveyor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='surveys',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.BOOKED,
    )
    site_suitable = models.BooleanField(null=True, blank=True)
    notes = models.TextField(blank=True)
    reschedule_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_at']
        verbose_name = 'Survey'
        verbose_name_plural = 'Surveys'

    def __str__(self) -> str:
        return f"Survey for {self.lead.name} at {self.scheduled_at.strftime('%Y-%m-%d %H:%M')} ({self.get_status_display()})"


class SurveyPhoto(models.Model):
    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name='photos',
    )
    image = models.ImageField(upload_to='surveys/%Y/%m/')
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Survey Photo'
        verbose_name_plural = 'Survey Photos'

    def __str__(self) -> str:
        return f"Photo for Survey #{self.survey_id}: {self.caption or self.image.name}"
