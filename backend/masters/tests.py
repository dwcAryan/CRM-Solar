from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from accounts.models import User
from leads.models import Lead
from masters.models import LeadSource, LostReason, NurtureReason, Outcome, PolicySettings
from quotes.models import Quote


class SeedMastersCommandTest(TestCase):
    def test_seed_masters_is_idempotent(self):
        # Run 1
        call_command('seed_masters')
        outcome_count_1 = Outcome.objects.count()
        lost_count_1 = LostReason.objects.count()
        nurture_count_1 = NurtureReason.objects.count()
        source_count_1 = LeadSource.objects.count()

        self.assertEqual(outcome_count_1, 29)  # 15 call + 7 survey + 7 quote
        self.assertEqual(lost_count_1, 11)
        self.assertEqual(nurture_count_1, 6)
        self.assertEqual(source_count_1, 6)
        self.assertEqual(PolicySettings.objects.count(), 1)

        # Run 2 (verify idempotency: no duplicates created)
        call_command('seed_masters')
        self.assertEqual(Outcome.objects.count(), outcome_count_1)
        self.assertEqual(LostReason.objects.count(), lost_count_1)
        self.assertEqual(NurtureReason.objects.count(), nurture_count_1)
        self.assertEqual(LeadSource.objects.count(), source_count_1)
        self.assertEqual(PolicySettings.objects.count(), 1)


class CoreModelsTest(TestCase):
    def setUp(self):
        call_command('seed_masters')
        self.user = User.objects.create_user(
            username='sales_agent',
            email='agent@solarcrm.com',
            password='Password123!',
            role=User.Role.SALESPERSON,
            phone='9876543210',
        )

    def test_user_roles(self):
        self.assertEqual(self.user.role, User.Role.SALESPERSON)
        self.assertEqual(self.user.phone, '9876543210')

    def test_lead_creation_and_status(self):
        lead = Lead.objects.create(
            name='Rajesh Sharma',
            phone='9876500000',
            city='Ahmedabad',
            status=Lead.Status.NEW,
            assigned_to=self.user,
        )
        self.assertIn(Lead.Status.WON, Lead.TERMINAL_STATUSES)
        self.assertEqual(lead.status, 'New')
        self.assertEqual(lead.attempt_count, 0)

    def test_quote_cannot_be_deleted(self):
        lead = Lead.objects.create(
            name='Sunita Verma',
            phone='9876511111',
            city='Surat',
        )
        quote = Quote.objects.create(
            lead=lead,
            version=1,
            system_size_kw=5.0,
            brand='Waaree 540W Mono PERC + Solis 5kW',
            price=275000.00,
            subsidy_amount=78000.00,
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            quote.delete()
