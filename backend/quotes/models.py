from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Quote(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent'
        REVISED = 'revised', 'Revised'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'

    lead = models.ForeignKey(
        'leads.Lead',
        on_delete=models.CASCADE,
        related_name='quotes',
    )
    version = models.PositiveIntegerField(default=1)

    # Multi-Country & Currency Snapshot Fields (Phase 8)
    region = models.ForeignKey(
        'masters.Region',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='quotes',
        help_text="Country/region this quotation was issued in.",
    )
    currency = models.CharField(max_length=10, default='INR', help_text="ISO currency e.g. INR, AUD")
    currency_symbol = models.CharField(max_length=10, default='₹', help_text="Currency symbol e.g. ₹, A$")
    tax_included = models.BooleanField(default=True, help_text="Whether price includes tax")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.0500, help_text="Tax rate snapshot at time of quotation")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Calculated tax portion")
    incentive_label = models.CharField(max_length=150, default='Subsidy', help_text="Region-specific incentive label snapshot")
    incentive_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Incentive / rebate / subsidy amount")
    battery_kwh = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Optional battery storage capacity in kWh")

    system_size_kw = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="System size in kilowatts (kW)",
    )
    brand = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total quote price in lead currency",
    )
    subsidy_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Legacy estimated subsidy amount (mapped to incentive_amount)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(blank=True)
    remark = models.CharField(max_length=500, blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_quotes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def populate_snapshots(self) -> None:
        if self.lead and not self.region:
            self.region = self.lead.region
        if self.region:
            self.currency = self.region.currency
            self.currency_symbol = self.region.currency_symbol
            if not self.pk:
                self.tax_rate = self.region.tax_rate
                self.incentive_label = self.region.incentive_label
            else:
                if not self.tax_rate:
                    self.tax_rate = self.region.tax_rate
                if not self.incentive_label:
                    self.incentive_label = self.region.incentive_label
        if self.subsidy_amount and (not self.incentive_amount or self.incentive_amount == 0):
            self.incentive_amount = self.subsidy_amount
        if self.price:
            rate = float(self.tax_rate or 0)
            p = float(self.price)
            if self.tax_included and rate > 0:
                self.tax_amount = round(p - (p / (1.0 + rate)), 2)
            else:
                self.tax_amount = round(p * rate, 2)

    def save(self, *args, **kwargs):
        self.populate_snapshots()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['lead', '-version']
        constraints = [
            models.UniqueConstraint(
                fields=['lead', 'version'],
                name='unique_lead_quote_version',
            )
        ]
        verbose_name = 'Quote'
        verbose_name_plural = 'Quotes'

    def delete(self, *args, **kwargs):
        raise ValidationError("Historical quotes cannot be deleted. Old versions must be preserved.")

    def __str__(self) -> str:
        return f"Quote v{self.version} for {self.lead.name} ({self.system_size_kw} kW - ₹{self.price})"
