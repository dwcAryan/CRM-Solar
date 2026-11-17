from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MANAGER = 'manager', 'Manager'
        SALESPERSON = 'salesperson', 'Salesperson'
        SURVEYOR = 'surveyor', 'Surveyor'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.SALESPERSON,
        help_text="Role determining user permissions and assignment eligibility.",
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact phone number.",
    )

    def __str__(self) -> str:
        full_name = self.get_full_name()
        display = full_name if full_name else self.username
        return f"{display} ({self.get_role_display()})"
