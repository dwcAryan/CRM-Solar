import datetime
import time
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from activities.models import Activity
from leads.models import Lead, LeadStatusHistory
from masters.models import Region, Outcome
from quotes.models import Quote
from quotes.pdf_service import generate_quote_pdf
from notifications.models import EmailOutbox
from notifications.outbox_service import process_outbox_batch, queue_email
from leads.history_renderer import render_history_text

User = get_user_model()


@pytest.fixture
def perf_setup(db):
    in_reg, _ = Region.objects.get_or_create(
        code='IN',
        defaults={'name': 'India', 'currency': 'INR', 'currency_symbol': '₹', 'default_timezone': 'Asia/Kolkata'},
    )
    au_reg, _ = Region.objects.get_or_create(
        code='AU',
        defaults={'name': 'Australia', 'currency': 'AUD', 'currency_symbol': '$', 'default_timezone': 'Australia/Sydney'},
    )

    admin = User.objects.create_user(
        username='perf_admin',
        password='Password123!',
        role='admin',
        is_staff=True,
    )
    admin.allowed_regions.set([in_reg, au_reg])

    manager = User.objects.create_user(
        username='perf_manager',
        password='Password123!',
        role='manager',
    )
    manager.allowed_regions.set([in_reg, au_reg])

    sp_in = User.objects.create_user(
        username='perf_sp_in',
        password='Password123!',
        role='salesperson',
        default_timezone='Asia/Kolkata',
    )
    sp_in.allowed_regions.set([in_reg])

    # Bulk create 5000 leads
    leads_to_create = []
    now = timezone.now()
    for i in range(5000):
        is_au = (i % 2 == 1)
        reg = au_reg if is_au else in_reg
        user = None if (i % 50 == 0) else (admin if (i % 3 == 0) else sp_in)
        status_val = Lead.Status.LOST_APPROVAL_PENDING if (i % 100 == 0) else (Lead.Status.NEW if i % 4 == 0 else Lead.Status.FOLLOW_UP)
        leads_to_create.append(
            Lead(
                name=f"Customer Sharma {i}" if i % 10 == 0 else f"Lead User {i}",
                phone=f"+6141234{i:04d}" if is_au else f"+9198765{i:04d}",
                email=f"perf_customer_{i}@example.com",
                region=reg,
                assigned_to=user,
                status=status_val,
                created_at=now - datetime.timedelta(days=(i % 365)),
                next_followup_at=now + datetime.timedelta(hours=i % 48),
            )
        )
    created_leads = Lead.objects.bulk_create(leads_to_create, batch_size=1000)

    # Bulk create 20000 activities across the leads
    activities_to_create = []
    for i in range(20000):
        lead = created_leads[i % 5000]
        activities_to_create.append(
            Activity(
                lead=lead,
                created_by=admin,
                type=Activity.Type.CALL,
                notes=f"Discussed rooftop solar feasibility notes #{i}",
                status_after=lead.status,
                created_at=now - datetime.timedelta(hours=i % 720),
            )
        )
    Activity.objects.bulk_create(activities_to_create, batch_size=2000)

    return {
        'admin': admin,
        'manager': manager,
        'sp_in': sp_in,
        'sample_lead': created_leads[0],
        'in_reg': in_reg,
        'au_reg': au_reg,
    }


@pytest.mark.django_db
class TestPhase16Performance:
    def test_leads_list_under_1_second(self, perf_setup):
        """Asserts leads list responds in < 1.0s on 5000 leads."""
        client = APIClient()
        client.force_authenticate(user=perf_setup['admin'])
        client.get('/api/me/')  # Warmup WSGI handler

        t0 = time.perf_counter()
        res = client.get('/api/leads/?page=1&page_size=25')
        duration = time.perf_counter() - t0

        assert res.status_code == 200
        assert duration < 1.0
        assert res.data['count'] >= 5000

    def test_leads_search_under_1_second(self, perf_setup):
        """Asserts search query executes in < 1.0s on 5000 leads."""
        client = APIClient()
        client.force_authenticate(user=perf_setup['admin'])
        client.get('/api/me/')  # Warmup WSGI handler

        t0 = time.perf_counter()
        res = client.get('/api/leads/?search=Sharma')
        duration = time.perf_counter() - t0

        assert res.status_code == 200
        assert duration < 1.0
        assert res.data['count'] > 0

    def test_leads_date_filter_under_1_second(self, perf_setup):
        """Asserts date range filter responds in < 1.0s."""
        client = APIClient()
        client.force_authenticate(user=perf_setup['admin'])
        client.get('/api/me/')  # Warmup WSGI handler

        t0 = time.perf_counter()
        res = client.get('/api/leads/?date_field=created_at&date_from=2025-01-01&date_to=2026-12-31')
        duration = time.perf_counter() - t0

        assert res.status_code == 200
        assert duration < 1.0

    def test_dashboard_roles_under_1_second(self, perf_setup):
        """Asserts dashboard computes aggregate metrics for all roles in < 1.0s."""
        client = APIClient()
        client.get('/api/me/')  # Warmup WSGI handler
        for role_user in [perf_setup['admin'], perf_setup['manager'], perf_setup['sp_in']]:
            client.force_authenticate(user=role_user)
            t0 = time.perf_counter()
            res = client.get('/api/dashboard/')
            duration = time.perf_counter() - t0

            assert res.status_code == 200
            assert duration < 1.0

    def test_today_and_manager_attention_queue_under_1_second(self, perf_setup):
        """Asserts today queue and manager attention queues respond in < 1.0s."""
        client = APIClient()
        client.force_authenticate(user=perf_setup['manager'])
        client.get('/api/me/')  # Warmup WSGI handler

        t0 = time.perf_counter()
        res_today = client.get('/api/leads/today/')
        duration_today = time.perf_counter() - t0
        assert res_today.status_code == 200
        assert duration_today < 1.0

        t0 = time.perf_counter()
        res_unassigned = client.get('/api/leads/unassigned/')
        duration_unassigned = time.perf_counter() - t0
        assert res_unassigned.status_code == 200
        assert duration_unassigned < 1.0

        t0 = time.perf_counter()
        res_lost = client.get('/api/leads/lost-approvals/')
        duration_lost = time.perf_counter() - t0
        assert res_lost.status_code == 200
        assert duration_lost < 1.0

    def test_pdf_generation_time_benchmark(self, perf_setup):
        """Asserts A4 PDF generation with TrueType Unicode font completes in < 1.5s."""
        lead = perf_setup['sample_lead']
        quote = Quote.objects.create(
            lead=lead,
            version=1,
            system_size_kw=Decimal('6.6'),
            brand='SunPower 400W & Fronius',
            price=Decimal('500000.00'),
            subsidy_amount=Decimal('78000.00'),
            created_by=perf_setup['admin'],
            region=perf_setup['in_reg'],
            currency='INR',
            currency_symbol='₹',
        )

        t0 = time.perf_counter()
        pdf_bytes = generate_quote_pdf(quote)
        duration = time.perf_counter() - t0

        assert len(pdf_bytes) > 1000
        assert duration < 1.5

    def test_email_outbox_processing_benchmark(self, perf_setup, settings):
        """Asserts processing batch of 30 emails completes in < 1.0s."""
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        EmailOutbox.objects.all().delete()

        for i in range(30):
            queue_email(
                to=f"bench_user_{i}@example.com",
                subject=f"Outbox Benchmark #{i}",
                template_name="daily_digest",
                plain_text=f"Body #{i}",
                html_content=f"<p>Batch email #{i}</p>",
            )

        t0 = time.perf_counter()
        processed = process_outbox_batch(limit=30)
        duration = time.perf_counter() - t0

        assert processed == 30
        assert duration < 1.0
