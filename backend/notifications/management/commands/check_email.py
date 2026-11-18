import sys
from django.conf import settings
from django.core.management.base import BaseCommand
from notifications.email_service import run_smtp_diagnostics


class Command(BaseCommand):
    help = "Verifies SMTP connectivity, TLS/SSL negotiation, and authentication credentials."

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            help="Recipient email address to deliver a live test email to upon successful authentication.",
        )

    def handle(self, *args, **options):
        to_email = options.get('to')

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Solar CRM Email (SMTP) Diagnostics ===\n"))

        # Mask password
        raw_pw = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        masked_pw = ("*" * len(raw_pw)) if raw_pw else "[Not Set]"

        self.stdout.write("Active Email Settings:")
        self.stdout.write(f"  EMAIL_BACKEND:       {getattr(settings, 'EMAIL_BACKEND', '')}")
        self.stdout.write(f"  EMAIL_HOST:          {getattr(settings, 'EMAIL_HOST', '')}")
        self.stdout.write(f"  EMAIL_PORT:          {getattr(settings, 'EMAIL_PORT', 587)}")
        self.stdout.write(f"  EMAIL_USE_TLS:       {getattr(settings, 'EMAIL_USE_TLS', False)}")
        self.stdout.write(f"  EMAIL_USE_SSL:       {getattr(settings, 'EMAIL_USE_SSL', False)}")
        self.stdout.write(f"  EMAIL_HOST_USER:     {getattr(settings, 'EMAIL_HOST_USER', '')}")
        self.stdout.write(f"  EMAIL_HOST_PASSWORD: {masked_pw}")
        self.stdout.write(f"  DEFAULT_FROM_EMAIL:  {getattr(settings, 'DEFAULT_FROM_EMAIL', '')}")
        self.stdout.write(f"  EMAIL_TIMEOUT:       {getattr(settings, 'EMAIL_TIMEOUT', 15)}s\n")

        self.stdout.write("Running Connection Checks:")
        diag = run_smtp_diagnostics(to_email=to_email)

        for step in diag["steps"]:
            status_text = "[ PASS ]" if step["status"] == "pass" else "[ FAIL ]"
            styled_status = self.style.SUCCESS(status_text) if step["status"] == "pass" else self.style.ERROR(status_text)
            self.stdout.write(f"  {styled_status} {step['name']}: {step['message']}")

        self.stdout.write("")
        if diag["overall_status"] == "pass":
            self.stdout.write(self.style.SUCCESS("✓ All SMTP diagnostics passed successfully.\n"))
        else:
            self.stdout.write(self.style.ERROR("✗ SMTP diagnostic check failed. Please resolve the issue indicated above.\n"))
            sys.exit(1)
