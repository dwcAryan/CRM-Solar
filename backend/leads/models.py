from django.conf import settings
from django.db import models


class ImportBatch(models.Model):
    file_name = models.CharField(max_length=255)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='import_batches',
    )
    imported_at = models.DateTimeField(auto_now_add=True)
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    duplicate_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    is_reverted = models.BooleanField(default=False)
    reverted_at = models.DateTimeField(null=True, blank=True)
    reverted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reverted_batches',
    )
    failed_rows_json = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-imported_at']
        verbose_name = 'Import Batch'
        verbose_name_plural = 'Import Batches'

    def __str__(self) -> str:
        status_str = "Reverted" if self.is_reverted else f"{self.imported_count} imported"
        return f"Batch #{self.id} ({self.file_name}) - {status_str}"


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = 'New', 'New'
        ATTEMPTING_CONTACT = 'Attempting contact', 'Attempting contact'
        CALLBACK_SCHEDULED = 'Callback scheduled', 'Callback scheduled'
        INVALID_CONTACT = 'Invalid contact', 'Invalid contact'
        FOLLOW_UP = 'Follow-up', 'Follow-up'
        INTERESTED = 'Interested', 'Interested'
        SURVEY_TO_SCHEDULE = 'Survey to schedule', 'Survey to schedule'
        SURVEY_SCHEDULED = 'Survey scheduled', 'Survey scheduled'
        SURVEY_RESCHEDULED = 'Survey rescheduled', 'Survey rescheduled'
        SURVEY_MISSED = 'Survey missed', 'Survey missed'
        DESIGN_PENDING = 'Design pending', 'Design pending'
        ALTERNATIVE = 'Alternative', 'Alternative'
        QUOTE_SENT = 'Quote sent', 'Quote sent'
        REVISING_QUOTE = 'Revising quote', 'Revising quote'
        NEGOTIATION = 'Negotiation', 'Negotiation'
        NURTURE = 'Nurture', 'Nurture'
        UNREACHABLE = 'Unreachable', 'Unreachable'
        WON = 'Won', 'Won'
        LOST = 'Lost', 'Lost'
        DO_NOT_CONTACT = 'Do not contact', 'Do not contact'
        MERGED = 'Merged', 'Merged'

    TERMINAL_STATUSES = {
        Status.WON,
        Status.LOST,
        Status.DO_NOT_CONTACT,
        Status.INVALID_CONTACT,
        Status.MERGED,
    }

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    alt_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    source = models.ForeignKey(
        'masters.LeadSource',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
    )
    property_type = models.CharField(max_length=50, blank=True)
    monthly_bill = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    roof_type = models.CharField(max_length=50, blank=True)
    owner_or_tenant = models.CharField(max_length=50, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads',
    )
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.NEW,
    )
    next_action = models.CharField(max_length=255, blank=True)
    next_followup_at = models.DateTimeField(null=True, blank=True)
    lost_reason = models.ForeignKey(
        'masters.LostReason',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
    )
    nurture_reason = models.ForeignKey(
        'masters.NurtureReason',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
    )
    do_not_contact = models.BooleanField(default=False)
    attempt_count = models.PositiveIntegerField(default=0)
    won_at = models.DateTimeField(null=True, blank=True)
    import_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
    )
    remark = models.CharField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['next_followup_at']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['phone']),
            models.Index(fields=['import_batch']),
        ]
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'

    def __str__(self) -> str:
        return f"{self.name} ({self.phone}) - {self.status}"


class LeadStatusHistory(models.Model):
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='status_history',
    )
    old_status = models.CharField(max_length=50)
    new_status = models.CharField(max_length=50)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_changes',
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)
    remark = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'Lead Status History'
        verbose_name_plural = 'Lead Status Histories'

    def __str__(self) -> str:
        return f"{self.lead.name}: {self.old_status} -> {self.new_status} at {self.changed_at}"


class AISuggestion(models.Model):
    class Provider(models.TextChoices):
        ANTHROPIC = 'anthropic', 'Anthropic Claude'
        RULES = 'rules', 'Rules Engine (Fallback)'

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='ai_suggestions',
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_ai_suggestions',
    )
    generated_at = models.DateTimeField(auto_now=True)
    provider = models.CharField(max_length=50, choices=Provider.choices, default=Provider.RULES)
    model = models.CharField(max_length=100, default='rules')
    input_hash = models.CharField(max_length=64, db_index=True)
    output_json = models.JSONField(default=dict)
    tokens_used = models.PositiveIntegerField(default=0)
    is_fallback = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-generated_at']
        verbose_name = 'AI Suggestion'
        verbose_name_plural = 'AI Suggestions'
        indexes = [
            models.Index(fields=['lead', 'input_hash']),
            models.Index(fields=['generated_at']),
        ]

    def __str__(self) -> str:
        return f"AISuggestion for Lead #{self.lead_id} ({self.provider}) at {self.generated_at}"
