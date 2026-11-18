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
    allowed_regions = models.ManyToManyField(
        'masters.Region',
        related_name='users',
        blank=True,
        help_text="Countries/regions this user is permitted to access.",
    )
    default_region = models.ForeignKey(
        'masters.Region',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text="Default country selected when creating leads.",
    )
    default_timezone = models.CharField(
        max_length=50,
        default='Asia/Kolkata',
        help_text="User's primary operating timezone for reminders and digest notifications.",
    )

    def __str__(self) -> str:
        full_name = self.get_full_name()
        display = full_name if full_name else self.username
        return f"{display} ({self.get_role_display()})"


class UserTourState(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        DISMISSED = 'dismissed', 'Dismissed'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tour_states')
    tour_id = models.CharField(max_length=50, default='main')
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    last_step = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'tour_id')
        verbose_name = 'User Tour State'
        verbose_name_plural = 'User Tour States'

    def __str__(self) -> str:
        return f"{self.user.username} - {self.tour_id} (v{self.version}): {self.status}"

