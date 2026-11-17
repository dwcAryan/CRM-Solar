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
    system_size_kw = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="System size in kilowatts (kW)",
    )
    brand = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total quote price in INR",
    )
    subsidy_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated government subsidy amount (informational)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_quotes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

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
