import getpass
import re

from django.core.management.base import BaseCommand

from accounts.models import User
from masters.models import Region


def validate_strong_password(password: str):
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters long.")
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter (A-Z).")
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter (a-z).")
    if not re.search(r'[0-9]', password):
        raise ValueError("Password must contain at least one digit (0-9).")
    if not re.search(r'[^A-Za-z0-9]', password):
        raise ValueError("Password must contain at least one special character (!@#$%^&* etc.).")


class Command(BaseCommand):
    help = "Creates an initial production administrator account with strict strong password enforcement."

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Administrator username')
        parser.add_argument('--email', type=str, help='Administrator email address')
        parser.add_argument('--password', type=str, help='Administrator password')
        parser.add_argument('--no-input', action='store_true', help='Non-interactive mode')

    def handle(self, *args, **options):
        no_input = options.get('no_input', False)
        username = options.get('username')
        email = options.get('email')
        password = options.get('password')

        self.stdout.write(self.style.NOTICE("=" * 60))
        self.stdout.write(self.style.NOTICE("SOLAR CRM - ADMINISTRATOR SETUP"))
        self.stdout.write(self.style.NOTICE("=" * 60))

        if not no_input:
            if not username:
                username = input("Enter admin username [admin]: ").strip() or "admin"
            if not email:
                email = input("Enter admin email [admin@example.com]: ").strip() or "admin@example.com"
            first_name = input("Enter first name [Admin]: ").strip() or "Admin"
            last_name = input("Enter last name [User]: ").strip() or "User"

            while not password:
                pwd1 = getpass.getpass("Enter strong password: ")
                try:
                    validate_strong_password(pwd1)
                except ValueError as err:
                    self.stdout.write(self.style.ERROR(f"Invalid password: {err}"))
                    continue

                pwd2 = getpass.getpass("Confirm password: ")
                if pwd1 != pwd2:
                    self.stdout.write(self.style.ERROR("Passwords do not match. Please try again."))
                    continue
                password = pwd1
        else:
            username = username or "admin"
            email = email or "admin@example.com"
            first_name = "Admin"
            last_name = "User"
            if not password:
                self.stdout.write(self.style.ERROR("--password is required when using --no-input."))
                return
            try:
                validate_strong_password(password)
            except ValueError as err:
                self.stdout.write(self.style.ERROR(f"Invalid password: {err}"))
                return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'is_demo': False,
                'must_change_password': False,
            }
        )

        user.role = User.Role.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.is_demo = False
        user.must_change_password = False
        user.set_password(password)
        user.save()

        # Assign all available regions
        active_regions = Region.objects.filter(is_active=True)
        if active_regions.exists():
            user.allowed_regions.set(active_regions)
            user.default_region = active_regions.first()
            user.save()

        action_str = "Created new" if created else "Updated existing"
        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully {action_str} administrator account '{username}'!"))
