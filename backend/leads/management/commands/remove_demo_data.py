import os

from django.core.management.base import BaseCommand
from django.db import models, transaction

from accounts.models import User, UserTourState
from activities.models import Activity
from helpbot.models import HelpbotQueryLog, HelpbotUnanswered
from leads.models import AuditLog, ImportBatch, Lead
from notifications.models import EmailLog, Notification, PushSubscription
from quotes.models import Quote
from surveys.models import Survey


class Command(BaseCommand):
    help = "Deletes all demo users and associated demo data (leads, activities, surveys, quotes, imports, notifications, audit entries) after confirmation."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            '--no-input',
            action='store_true',
            help='Skip typed confirmation and immediately delete demo data.',
        )

    def handle(self, *args, **options):
        demo_users = User.objects.filter(models.Q(is_demo=True) | models.Q(username__startswith='demo_'))
        user_count = demo_users.count()

        if user_count == 0:
            self.stdout.write(self.style.WARNING("No demo users or demo data found in database."))
            return

        demo_leads = Lead.objects.filter(models.Q(assigned_to__in=demo_users) | models.Q(created_by__in=demo_users))
        lead_count = demo_leads.count()
        activity_count = Activity.objects.filter(models.Q(created_by__in=demo_users) | models.Q(lead__in=demo_leads)).count()
        survey_count = Survey.objects.filter(models.Q(surveyor__in=demo_users) | models.Q(lead__in=demo_leads)).count()
        quote_count = Quote.objects.filter(models.Q(created_by__in=demo_users) | models.Q(lead__in=demo_leads)).count()
        import_batch_count = ImportBatch.objects.filter(imported_by__in=demo_users).count()
        notification_count = Notification.objects.filter(user__in=demo_users).count()
        push_sub_count = PushSubscription.objects.filter(user__in=demo_users).count()
        email_log_count = EmailLog.objects.filter(
            models.Q(related_lead__in=demo_leads) | models.Q(to__in=demo_users.values_list('email', flat=True))
        ).count()
        audit_log_count = AuditLog.objects.filter(user__in=demo_users).count()

        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write(self.style.WARNING("DEMO DATA INVENTORY FOR REMOVAL:"))
        self.stdout.write(f"  Demo Users:            {user_count}")
        self.stdout.write(f"  Associated Leads:      {lead_count}")
        self.stdout.write(f"  Activities:            {activity_count}")
        self.stdout.write(f"  Surveys:               {survey_count}")
        self.stdout.write(f"  Quotes:                {quote_count}")
        self.stdout.write(f"  Import Batches:        {import_batch_count}")
        self.stdout.write(f"  Notifications:         {notification_count}")
        self.stdout.write(f"  Push Subscriptions:    {push_sub_count}")
        self.stdout.write(f"  Email Logs:            {email_log_count}")
        self.stdout.write(f"  Audit Log Entries:     {audit_log_count}")
        self.stdout.write(self.style.WARNING("=" * 60))

        if not options.get('force'):
            self.stdout.write("To permanently delete all demo data, type 'delete demo' or 'yes': ")
            confirm = input().strip().lower()
            if confirm not in ['delete demo', 'yes', 'y']:
                self.stdout.write(self.style.NOTICE("Aborted. No demo data was deleted."))
                return

        self.stdout.write("Deleting demo data...")
        with transaction.atomic():
            Activity.objects.filter(models.Q(created_by__in=demo_users) | models.Q(lead__in=demo_leads)).delete()
            Survey.objects.filter(models.Q(surveyor__in=demo_users) | models.Q(lead__in=demo_leads)).delete()
            Quote.objects.filter(models.Q(created_by__in=demo_users) | models.Q(lead__in=demo_leads)).delete()
            EmailLog.objects.filter(
                models.Q(related_lead__in=demo_leads) | models.Q(to__in=demo_users.values_list('email', flat=True))
            ).delete()
            PushSubscription.objects.filter(user__in=demo_users).delete()
            Notification.objects.filter(user__in=demo_users).delete()
            AuditLog.objects.filter(user__in=demo_users).delete()
            UserTourState.objects.filter(user__in=demo_users).delete()
            HelpbotQueryLog.objects.filter(user__in=demo_users).delete()
            HelpbotUnanswered.objects.filter(user__in=demo_users).delete()
            ImportBatch.objects.filter(imported_by__in=demo_users).delete()
            demo_leads.delete()
            demo_users.delete()

        # Clean demo accounts doc if exists
        doc_path = os.path.join('docs', 'DEMO_ACCOUNTS.md')
        if os.path.exists(doc_path):
            try:
                os.remove(doc_path)
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS("All demo users and demo data successfully removed from database!"))
