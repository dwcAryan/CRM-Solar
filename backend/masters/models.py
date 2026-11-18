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
    data_retention_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of days to retain closed lead PII before automatic anonymization. Null or 0 means disabled.",
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


class Region(models.Model):
    class CallingHoursPolicy(models.TextChoices):
        WARN = 'warn', 'Warn Salesperson'
        BLOCK = 'block', 'Block Call Logging'

    code = models.CharField(max_length=2, primary_key=True, help_text="ISO 2-letter country code e.g. IN, AU")
    name = models.CharField(max_length=100)
    currency = models.CharField(max_length=10, default='INR', help_text="ISO currency code e.g. INR, AUD")
    currency_symbol = models.CharField(max_length=10, default='₹', help_text="Display symbol e.g. ₹, A$")
    default_timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    phone_country_code = models.CharField(max_length=10, default='+91', help_text="Dialing prefix e.g. +91, +61")
    locale = models.CharField(max_length=20, default='en-IN', help_text="Intl locale e.g. en-IN, en-AU")
    tax_label = models.CharField(max_length=50, default='GST')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.0500, help_text="Default tax rate (e.g. 0.05 for 5%, 0.10 for 10%)")
    incentive_label = models.CharField(max_length=150, default='Subsidy', help_text="Local incentive terminology e.g. Subsidy or Government incentive (STCs and rebates)")
    electricity_provider_label = models.CharField(max_length=100, default='DISCOM', help_text="Provider terminology e.g. DISCOM or Electricity retailer")
    preferred_channels = models.JSONField(default=list, help_text="List of channels in priority order e.g. ['whatsapp', 'sms'] or ['sms', 'whatsapp']")
    calling_hours_start = models.TimeField(default='09:00:00')
    calling_hours_end_weekday = models.TimeField(default='20:00:00')
    calling_hours_end_saturday = models.TimeField(default='17:00:00')
    sunday_calling_allowed = models.BooleanField(default=False)
    sunday_hours_start = models.TimeField(null=True, blank=True)
    sunday_hours_end = models.TimeField(null=True, blank=True)
    calling_hours_policy = models.CharField(max_length=20, choices=CallingHoursPolicy.choices, default=CallingHoursPolicy.WARN)
    dncr_validity_days = models.PositiveIntegerField(default=30, help_text="Validity period in days for Do-Not-Call register check")
    opt_out_text = models.CharField(max_length=255, default='Reply STOP to opt out')
    privacy_notice_text = models.TextField(blank=True, default='')
    region_notes = models.TextField(blank=True, default='', help_text="Market context, incentives, feed-in tariffs, and rules for sales guidance and AI prompt.")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'code']
        verbose_name = 'Region'
        verbose_name_plural = 'Regions'

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class State(models.Model):
    code = models.CharField(max_length=10, help_text="State code e.g. NSW, VIC, MH, DL")
    name = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='states')
    default_timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['region', 'sort_order', 'name']
        unique_together = [('region', 'code')]
        verbose_name = 'State / Territory'
        verbose_name_plural = 'States & Territories'

    def __str__(self) -> str:
        return f"{self.name} ({self.code}) - {self.region.code}"


class PublicHoliday(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='holidays')
    date = models.DateField()
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ['region', 'date']
        unique_together = [('region', 'date')]
        verbose_name = 'Public Holiday'
        verbose_name_plural = 'Public Holidays'

    def __str__(self) -> str:
        return f"{self.name} ({self.date}) - {self.region.code}"


class RoofType(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='roof_types')
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['region', 'sort_order', 'name']
        unique_together = [('region', 'name')]
        verbose_name = 'Roof Type'
        verbose_name_plural = 'Roof Types'

    def __str__(self) -> str:
        return f"{self.name} ({self.region.code})"


class PropertyType(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='property_types')
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['region', 'sort_order', 'name']
        unique_together = [('region', 'name')]
        verbose_name = 'Property Type'
        verbose_name_plural = 'Property Types'

    def __str__(self) -> str:
        return f"{self.name} ({self.region.code})"
