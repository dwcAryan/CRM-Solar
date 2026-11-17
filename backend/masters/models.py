from django.db import models


class Outcome(models.Model):
    class Stage(models.TextChoices):
        CALL = 'call', 'Call'
        SURVEY = 'survey', 'Survey'
        QUOTE = 'quote', 'Quote'

    stage = models.CharField(max_length=20, choices=Stage.choices)
    name = models.CharField(max_length=150)
    default_status = models.CharField(max_length=50)
    default_next_action = models.CharField(max_length=255)
    default_followup_days = models.IntegerField(null=True, blank=True)
    followup_date_required_manually = models.BooleanField(default=False)
    is_terminal = models.BooleanField(default=False)
    requires_lost_reason = models.BooleanField(default=False)
    requires_nurture_reason = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['stage', 'sort_order', 'id']
        verbose_name = 'Outcome'
        verbose_name_plural = 'Outcomes'

    def __str__(self) -> str:
        return f"[{self.get_stage_display()}] {self.name} -> {self.default_status}"


class LostReason(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Lost Reason'
        verbose_name_plural = 'Lost Reasons'

    def __str__(self) -> str:
        return self.name


class NurtureReason(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Nurture Reason'
        verbose_name_plural = 'Nurture Reasons'

    def __str__(self) -> str:
        return self.name


class LeadSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Lead Source'
        verbose_name_plural = 'Lead Sources'

    def __str__(self) -> str:
        return self.name


class PolicySettings(models.Model):
    max_call_attempts_before_unreachable = models.PositiveIntegerField(
        default=5,
        help_text="Attempts before auto-moving lead to Unreachable.",
    )
    unreachable_followup_days = models.PositiveIntegerField(
        default=14,
        help_text="Follow-up days assigned when moving to Unreachable.",
    )
    nurture_default_days = models.PositiveIntegerField(
        default=90,
        help_text="Default days for nurture follow-up.",
    )
    who_can_mark_lost = models.CharField(
        max_length=50,
        default='manager',
        help_text="Role allowed to mark a lead as Lost (e.g., manager, admin).",
    )

    class Meta:
        verbose_name = 'Policy Settings'
        verbose_name_plural = 'Policy Settings'

    def save(self, *args, **kwargs):
        # Enforce singleton pattern
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> 'PolicySettings':
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        return "Global Policy Settings"
