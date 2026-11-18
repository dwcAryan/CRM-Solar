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
        LOST_APPROVAL_PENDING = 'Lost approval pending', 'Lost approval pending'
        DO_NOT_CONTACT = 'Do not contact', 'Do not contact'
        MERGED = 'Merged', 'Merged'

    TERMINAL_STATUSES = {
        Status.WON,
        Status.LOST,
        Status.DO_NOT_CONTACT,
        Status.INVALID_CONTACT,
        Status.MERGED,
    }

    class BillPeriod(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        TWO_MONTHLY = 'two_monthly', 'Two-Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        ANNUAL = 'annual', 'Annual'

    class ConsentStatus(models.TextChoices):
        CONSENTED = 'consented', 'Consented'
        UNKNOWN = 'unknown', 'Unknown'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    class DNCRStatus(models.TextChoices):
        NOT_CHECKED = 'not_checked', 'Not Checked'
        ON_REGISTER = 'on_register', 'On Register (Do Not Call)'
        NOT_ON_REGISTER = 'not_on_register', 'Not On Register (Clear to Call)'

    # Multi-Country & Geographic Fields (Phase 8)
    region = models.ForeignKey(
        'masters.Region',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='leads',
        help_text="Country/region this lead belongs to (e.g. IN, AU).",
    )
    state_ref = models.ForeignKey(
        'masters.State',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
        help_text="Normalized state/territory reference.",
    )
    state = models.CharField(max_length=100, blank=True, help_text="State or territory text.")
    timezone = models.CharField(max_length=50, default='Asia/Kolkata', help_text="Lead local timezone derived from state with override.")

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    phone_e164 = models.CharField(max_length=25, blank=True, db_index=True, help_text="E.164 formatted contact phone (+91..., +61...)")
    phone_raw_backup = models.CharField(max_length=50, blank=True, help_text="Pre-migration raw phone string for rollback.")
    alt_phone = models.CharField(max_length=30, blank=True)
    alt_phone_e164 = models.CharField(max_length=25, blank=True, help_text="E.164 formatted alternate phone")
    alt_phone_raw_backup = models.CharField(max_length=50, blank=True, help_text="Pre-migration raw alt phone string for rollback.")
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True, help_text="City or suburb.")
    suburb = models.CharField(max_length=100, blank=True, help_text="Suburb for Australian leads.")
    pincode = models.CharField(max_length=20, blank=True, help_text="Indian 6-digit pincode or Australian 4-digit postcode.")
    postcode = models.CharField(max_length=20, blank=True, help_text="Australian 4-digit postcode.")
    source = models.ForeignKey(
        'masters.LeadSource',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
    )
    property_type = models.CharField(max_length=100, blank=True)
    roof_type = models.CharField(max_length=100, blank=True)
    owner_or_tenant = models.CharField(max_length=50, blank=True)

    # Electricity Bill & Provider (Phase 8)
    bill_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Billed amount in lead currency.")
    bill_period = models.CharField(max_length=20, choices=BillPeriod.choices, default=BillPeriod.MONTHLY)
    normalized_monthly_bill = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Normalized monthly bill estimate.")
    monthly_bill = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Legacy monthly bill amount.")
    electricity_provider = models.CharField(max_length=150, blank=True, help_text="DISCOM (IN) or Electricity retailer (AU).")

    # Consent & Regulatory Controls (Phase 8)
    consent_status = models.CharField(max_length=20, choices=ConsentStatus.choices, default=ConsentStatus.UNKNOWN)
    consent_source = models.CharField(max_length=100, blank=True, help_text="Source of consent: Website form, Inbound call, Import, etc.")
    consent_date = models.DateTimeField(null=True, blank=True)
    opt_out_calls = models.BooleanField(default=False)
    opt_out_sms = models.BooleanField(default=False)
    opt_out_whatsapp = models.BooleanField(default=False)
    opt_out_email = models.BooleanField(default=False)
    dncr_status = models.CharField(max_length=20, choices=DNCRStatus.choices, default=DNCRStatus.NOT_CHECKED)
    dncr_checked_at = models.DateTimeField(null=True, blank=True)
    dncr_checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
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
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_leads',
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_leads',
    )
    deleted_reason = models.CharField(max_length=500, blank=True, default='')
    lost_pending_reason = models.ForeignKey(
        'masters.LostReason',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_lost_leads',
    )
    lost_pending_notes = models.TextField(blank=True, default='')
    previous_status_before_lost = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['next_followup_at']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['phone']),
            models.Index(fields=['phone_e164']),
            models.Index(fields=['region']),
            models.Index(fields=['import_batch']),
        ]
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'

    def save(self, *args, **kwargs):
        # Auto-populate phone_e164 if not explicitly set
        if self.phone and not self.phone_e164:
            from .phone_utils import normalize_phone_number
            e164, _, _ = normalize_phone_number(self.phone, self.region_id or 'IN')
            if e164:
                self.phone_e164 = e164

        # Normalize monthly bill if bill amount is present
        if self.bill_amount is not None:
            amt = float(self.bill_amount)
            if self.bill_period == self.BillPeriod.MONTHLY:
                self.normalized_monthly_bill = amt
            elif self.bill_period == self.BillPeriod.TWO_MONTHLY:
                self.normalized_monthly_bill = round(amt / 2.0, 2)
            elif self.bill_period == self.BillPeriod.QUARTERLY:
                self.normalized_monthly_bill = round(amt / 3.0, 2)
            elif self.bill_period == self.BillPeriod.ANNUAL:
                self.normalized_monthly_bill = round(amt / 12.0, 2)
            self.monthly_bill = self.normalized_monthly_bill
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        reg = f"[{self.region_id}] " if self.region_id else ""
        return f"{reg}{self.name} ({self.phone_e164 or self.phone}) - {self.status}"


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


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    user_name = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=100, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    lead_id_recorded = models.IntegerField(null=True, blank=True)
    reason = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['lead_id_recorded']),
        ]

    def __str__(self) -> str:
        lead_str = f" (Lead #{self.lead_id_recorded})" if self.lead_id_recorded else ""
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.action} by {self.user_name or 'System'}{lead_str}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("AuditLog entries are tamper-evident and immutable: updates are strictly forbidden.")
        if self.user and not self.user_name:
            self.user_name = self.user.get_full_name() or self.user.username
        if self.lead and not self.lead_id_recorded:
            self.lead_id_recorded = self.lead.id
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditLog entries are tamper-evident and immutable: deletions are strictly forbidden.")

