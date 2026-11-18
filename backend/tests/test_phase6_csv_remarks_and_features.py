from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.models import User
from leads.import_service import sanitize_csv_cell
from leads.models import ImportBatch, Lead
from masters.models import LeadSource, LostReason, Outcome


@pytest.fixture
def sales_user(db):
    return User.objects.create_user(
        username='phase6_sales',
        email='sales@example.com',
        password='password123',
        role=User.Role.SALESPERSON,
        phone='9825000001',
    )


@pytest.fixture
def manager_user(db):
    return User.objects.create_user(
        username='phase6_manager',
        email='manager@example.com',
        password='password123',
        role=User.Role.MANAGER,
        phone='9825000002',
    )


@pytest.fixture
def sample_source(db):
    source, _ = LeadSource.objects.get_or_create(name='Website Form', defaults={'is_active': True})
    return source


@pytest.fixture
def lost_reason(db):
    reason, _ = LostReason.objects.get_or_create(name='Competitor cheaper', defaults={'is_active': True})
    return reason


@pytest.mark.django_db
class TestCsvLeadImport:
    def test_sample_csv_download_and_sanitization(self, client, sales_user):
        client.force_login(sales_user)
        response = client.get('/api/leads/import-sample-csv/')
        assert response.status_code == 200
        assert 'text/csv' in response['Content-Type']
        assert 'solar_leads_sample_template.csv' in response['Content-Disposition']
        content = response.content.decode('utf-8-sig')
        assert 'Name,Phone,Email,City' in content
        assert 'Ramesh Patel' in content

    def test_sanitize_csv_cell_formula_injection(self):
        # Formula injection characters: = + - @
        assert sanitize_csv_cell("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"
        assert sanitize_csv_cell("+12345") == "'+12345"
        assert sanitize_csv_cell("-12345") == "'-12345"
        assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
        assert sanitize_csv_cell("Safe String") == "Safe String"
        assert sanitize_csv_cell(123) == "123"

    def test_preview_csv_endpoint(self, client, sales_user):
        client.force_login(sales_user)
        csv_data = (
            "Customer Name,Mobile Number,Town,Monthly Power Bill\n"
            "Anil Sharma,+91 98250 11111,Ahmedabad,4500\n"
            "Geeta Ben,9825022222,Surat,6000\n"
        ).encode('utf-8-sig')
        file_obj = SimpleUploadedFile("leads.csv", csv_data, content_type="text/csv")

        response = client.post('/api/leads/preview-csv/', {'file': file_obj})
        assert response.status_code == 200
        data = response.json()
        assert data['total_rows'] == 2
        assert 'Customer Name' in data['headers']
        assert data['suggested_mapping']['name'] == 'Customer Name'
        assert data['suggested_mapping']['phone'] == 'Mobile Number'
        assert len(data['preview_rows']) == 2
        assert data['preview_rows'][0]['Customer Name'] == 'Anil Sharma'

    def test_import_valid_file_and_followup_rule(self, client, manager_user, sample_source):
        client.force_login(manager_user)
        csv_data = (
            "Name,Phone,Email,City,Source,Monthly Bill,Remark\n"
            "Harish Bhai,98250 33333,harish@example.com,Vadodara,Website Form,5500,Needs 4kW system\n"
            "Bhavna Patel,+91-98250-44444,bhavna@example.com,Ahmedabad,Website Form,4000,Interested in subsidy\n"
        ).encode('utf-8-sig')
        file_obj = SimpleUploadedFile("valid_leads.csv", csv_data, content_type="text/csv")

        mapping = '{"name":"Name","phone":"Phone","email":"Email","city":"City","source":"Source","monthly_bill":"Monthly Bill","remark":"Remark"}'
        response = client.post(
            '/api/leads/import-csv/',
            {
                'file': file_obj,
                'mapping': mapping,
                'duplicate_action': 'skip',
                'assignment_mode': 'single',
                'assigned_to_id': manager_user.id,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data['imported_count'] == 2
        assert data['failed_count'] == 0
        assert data['duplicate_count'] == 0

        # Verify leads in database
        lead1 = Lead.objects.get(phone='9825033333')
        assert lead1.name == 'Harish Bhai'
        assert lead1.status == Lead.Status.NEW
        assert lead1.next_action == 'First call attempt'
        assert lead1.next_followup_at is not None
        # Follow-up rule: imported leads must have next_followup_at scheduled for today!
        assert lead1.next_followup_at.date() == timezone.now().date()
        assert lead1.assigned_to == manager_user
        assert lead1.remark == 'Needs 4kW system'
        assert lead1.import_batch_id == data['batch_id']

    def test_import_with_bad_phones_and_row_error_reporting(self, client, manager_user):
        client.force_login(manager_user)
        csv_data = (
            "Name,Phone\n"
            ",9825055555\n"  # missing name
            "Valid Person,9825066666\n"
            "Bad Phone Person,12345\n"  # invalid length
            "Letters Phone,98250ABCDE\n"  # invalid characters
        ).encode('utf-8-sig')
        file_obj = SimpleUploadedFile("bad_leads.csv", csv_data, content_type="text/csv")

        mapping = '{"name":"Name","phone":"Phone"}'
        response = client.post(
            '/api/leads/import-csv/',
            {
                'file': file_obj,
                'mapping': mapping,
                'duplicate_action': 'skip',
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data['imported_count'] == 1
        assert data['failed_count'] == 3
        assert len(data['errors']) == 3
        assert any("Name is required" in err['error'] for err in data['errors'])
        assert any("Must normalize to 10 digits" in err['error'] for err in data['errors'])

    def test_duplicates_inside_file_and_in_database(self, client, manager_user):
        client.force_login(manager_user)
        # Pre-existing lead in database
        Lead.objects.create(
            name="Existing DB Customer",
            phone="9825077777",
            status=Lead.Status.NEW,
            city="Ahmedabad",
            next_followup_at=timezone.now(),
        )

        csv_data = (
            "Name,Phone,City\n"
            "DB Duplicate,9825077777,Surat\n"  # dup with DB
            "File Dup First,9825088888,Rajkot\n"
            "File Dup Second,9825088888,Rajkot\n"  # dup with row 3
            "Unique Person,9825099991,Baroda\n"
        ).encode('utf-8-sig')
        file_obj = SimpleUploadedFile("dup_leads.csv", csv_data, content_type="text/csv")

        mapping = '{"name":"Name","phone":"Phone","city":"City"}'
        response = client.post(
            '/api/leads/import-csv/',
            {
                'file': file_obj,
                'mapping': mapping,
                'duplicate_action': 'skip',
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data['imported_count'] == 2  # File Dup First + Unique Person
        assert data['duplicate_count'] == 2  # DB Duplicate + File Dup Second
        assert data['skipped_count'] == 2

    def test_duplicate_action_update_empty_fields(self, client, manager_user):
        client.force_login(manager_user)
        # Pre-existing lead with empty email and monthly_bill
        existing = Lead.objects.create(
            name="Partial Customer",
            phone="9825077788",
            city="Ahmedabad",
            email="",
            monthly_bill=None,
            status=Lead.Status.NEW,
            next_followup_at=timezone.now(),
        )

        csv_data = (
            "Name,Phone,Email,Monthly Bill\n"
            "Partial Customer,9825077788,updated@example.com,7500\n"
        ).encode('utf-8-sig')
        file_obj = SimpleUploadedFile("update_leads.csv", csv_data, content_type="text/csv")

        mapping = '{"name":"Name","phone":"Phone","email":"Email","monthly_bill":"Monthly Bill"}'
        response = client.post(
            '/api/leads/import-csv/',
            {
                'file': file_obj,
                'mapping': mapping,
                'duplicate_action': 'update_empty',
            },
        )
        assert response.status_code == 201
        existing.refresh_from_db()
        assert existing.email == 'updated@example.com'
        assert existing.monthly_bill == Decimal('7500.00')

    def test_round_robin_assignment(self, client, manager_user, sales_user):
        sales2 = User.objects.create_user(
            username='sales2_rr',
            password='password123',
            role=User.Role.SALESPERSON,
            phone='9825000003',
        )
        client.force_login(manager_user)

        csv_data = (
            "Name,Phone\n"
            "Lead One,9825100001\n"
            "Lead Two,9825100002\n"
            "Lead Three,9825100003\n"
            "Lead Four,9825100004\n"
        ).encode('utf-8-sig')
        file_obj = SimpleUploadedFile("rr_leads.csv", csv_data, content_type="text/csv")

        mapping = '{"name":"Name","phone":"Phone"}'
        response = client.post(
            '/api/leads/import-csv/',
            {
                'file': file_obj,
                'mapping': mapping,
                'assignment_mode': 'round_robin',
                'round_robin_user_ids': f"{sales_user.id},{sales2.id}",
            },
        )
        assert response.status_code == 201

        assigned_sales = list(Lead.objects.filter(phone__startswith='982510000').order_by('id').values_list('assigned_to_id', flat=True))
        assert assigned_sales == [sales_user.id, sales2.id, sales_user.id, sales2.id]

    def test_undo_import_batch(self, client, manager_user):
        client.force_login(manager_user)
        csv_data = (
            "Name,Phone\n"
            "Undo Lead 1,9825200001\n"
            "Undo Lead 2,9825200002\n"
        ).encode('utf-8-sig')
        file_obj = SimpleUploadedFile("undo_batch.csv", csv_data, content_type="text/csv")

        res = client.post('/api/leads/import-csv/', {'file': file_obj, 'mapping': '{"name":"Name","phone":"Phone"}'})
        batch_id = res.json()['batch_id']
        assert Lead.objects.filter(import_batch_id=batch_id).count() == 2

        # Undo batch
        undo_res = client.post(f'/api/import-batches/{batch_id}/undo/')
        assert undo_res.status_code == 200
        assert undo_res.json()['deleted_count'] == 2
        assert Lead.objects.filter(import_batch_id=batch_id).count() == 0

        batch = ImportBatch.objects.get(id=batch_id)
        assert batch.is_reverted is True
        assert batch.reverted_by == manager_user

    def test_malicious_file_handling(self, client, manager_user):
        client.force_login(manager_user)
        # 1. Invalid file extension
        bad_ext = SimpleUploadedFile("script.sh", b"echo 'hack'", content_type="application/x-sh")
        res1 = client.post('/api/leads/import-csv/', {'file': bad_ext})
        assert res1.status_code == 400
        assert "Only .csv and .xlsx files are supported" in res1.json()['error']

        # 2. Oversized file (> 5 MB)
        big_content = b"0" * (5 * 1024 * 1024 + 10)
        big_file = SimpleUploadedFile("big.csv", big_content, content_type="text/csv")
        res2 = client.post('/api/leads/import-csv/', {'file': big_file})
        assert res2.status_code == 400
        assert "exceeds maximum allowed limit of 5 MB" in res2.json()['error']


@pytest.mark.django_db
class TestOptionalRemarksOnEveryStep:
    def test_create_lead_with_and_without_remark(self, client, sales_user):
        client.force_login(sales_user)
        # Without remark
        res1 = client.post('/api/leads/', {
            'name': 'No Remark Customer',
            'phone': '9825300001',
            'city': 'Ahmedabad',
        })
        assert res1.status_code == 201
        assert res1.json()['remark'] == ''

        # With remark
        res2 = client.post('/api/leads/', {
            'name': 'With Remark Customer',
            'phone': '9825300002',
            'city': 'Surat',
            'remark': 'Referred by colony neighbor Mr. Gupta',
        })
        assert res2.status_code == 201
        assert res2.json()['remark'] == 'Referred by colony neighbor Mr. Gupta'

    def test_add_remark_endpoint(self, client, sales_user):
        client.force_login(sales_user)
        lead = Lead.objects.create(
            name="Remark Test Lead",
            phone="9825300003",
            status=Lead.Status.INTERESTED,
            next_action="Send details",
            next_followup_at=timezone.now(),
            assigned_to=sales_user,
        )

        res = client.post(f'/api/leads/{lead.id}/add-remark/', {
            'remark': 'Customer requested afternoon call after 3 PM.',
        })
        assert res.status_code == 201
        lead.refresh_from_db()
        assert lead.remark == 'Customer requested afternoon call after 3 PM.'
        assert lead.status == Lead.Status.INTERESTED  # status unchanged
        assert lead.activities.filter(type='note', remark='Customer requested afternoon call after 3 PM.').exists()

    def test_log_activity_with_and_without_remark(self, client, sales_user):
        client.force_login(sales_user)
        outcome, _ = Outcome.objects.get_or_create(
            stage=Outcome.Stage.CALL,
            name='Interested',
            defaults={
                'default_status': 'Interested',
                'default_next_action': 'Send info',
                'default_followup_days': 2,
            },
        )
        lead = Lead.objects.create(
            name="Activity Remark Lead",
            phone="9825300004",
            status=Lead.Status.NEW,
            assigned_to=sales_user,
        )

        followup = (timezone.now() + timezone.timedelta(days=2)).isoformat()
        res = client.post(f'/api/leads/{lead.id}/log-activity/', {
            'type': 'call',
            'outcome_id': outcome.id,
            'next_followup_at': followup,
            'remark': 'Wife is interested in saving power bill, husband away till Friday',
        })
        assert res.status_code == 200
        lead.refresh_from_db()
        assert lead.remark == 'Wife is interested in saving power bill, husband away till Friday'
        act = lead.activities.first()
        assert act.remark == 'Wife is interested in saving power bill, husband away till Friday'

    def test_survey_and_quote_remarks(self, client, sales_user, lost_reason):
        client.force_login(sales_user)
        lead = Lead.objects.create(
            name="Survey Quote Remark Lead",
            phone="9825300005",
            status=Lead.Status.SURVEY_TO_SCHEDULE,
            assigned_to=sales_user,
        )

        # 1. Book Survey with remark
        sched = (timezone.now() + timezone.timedelta(days=1)).isoformat()
        res_survey = client.post('/api/surveys/book/', {
            'lead_id': lead.id,
            'scheduled_at': sched,
            'notes': 'Check roof shadows',
            'remark': 'Customer requested survey engineer to remove footwear before terrace',
        })
        assert res_survey.status_code == 201
        assert res_survey.json()['remark'] == 'Customer requested survey engineer to remove footwear before terrace'

        # 2. Create Quote with remark
        res_quote = client.post('/api/quotes/', {
            'lead_id': lead.id,
            'system_size_kw': 5.0,
            'brand': 'Adani 540W Mono',
            'price': 250000,
            'subsidy_amount': 78000,
            'notes': '5kW standard package',
            'remark': 'Special festival discount coupon applied',
        })
        assert res_quote.status_code == 201
        assert res_quote.json()['remark'] == 'Special festival discount coupon applied'


@pytest.mark.django_db
class TestEaseOfUseFeatures:
    def test_bulk_actions_assign_and_change_source(self, client, manager_user, sales_user, sample_source):
        client.force_login(manager_user)
        l1 = Lead.objects.create(name="L1", phone="9825400001", status="New")
        l2 = Lead.objects.create(name="L2", phone="9825400002", status="New")

        # 1. Bulk assign to salesperson
        res_assign = client.post('/api/leads/bulk-action/', {
            'lead_ids': [l1.id, l2.id],
            'action': 'assign',
            'value': sales_user.id,
            'remark': 'Assigned via East Zone distribution',
        }, content_type='application/json')
        assert res_assign.status_code == 200
        assert res_assign.json()['updated_count'] == 2

        l1.refresh_from_db()
        l2.refresh_from_db()
        assert l1.assigned_to == sales_user
        assert l2.assigned_to == sales_user
        assert l1.remark == 'Assigned via East Zone distribution'

        # 2. Bulk change source
        res_src = client.post('/api/leads/bulk-action/', {
            'lead_ids': [l1.id, l2.id],
            'action': 'change_source',
            'value': sample_source.id,
        }, content_type='application/json')
        assert res_src.status_code == 200
        l1.refresh_from_db()
        assert l1.source == sample_source

    def test_export_leads_csv_with_formula_escaping(self, client, manager_user):
        client.force_login(manager_user)
        # Create lead with potential formula injection string
        Lead.objects.create(
            name="=SUM(A1:A10)",
            phone="9825500001",
            city="+Ahmedabad",
            status="New",
            remark="@test_handle",
        )

        res = client.get('/api/leads/export-csv/')
        assert res.status_code == 200
        assert 'text/csv' in res['Content-Type']
        content = res.content.decode('utf-8-sig')

        # Check that characters starting with =, +, @ are escaped with leading apostrophe
        assert "'=SUM(A1:A10)" in content
        assert "'+Ahmedabad" in content
        assert "'@test_handle" in content

    def test_saved_filter_tabs(self, client, sales_user):
        client.force_login(sales_user)
        now = timezone.now()

        # My lead
        Lead.objects.create(name="My Lead", phone="9825600001", assigned_to=sales_user, status="New")
        # Overdue lead
        Lead.objects.create(
            name="Overdue Lead",
            phone="9825600002",
            assigned_to=sales_user,
            status="Interested",
            next_followup_at=now - timezone.timedelta(days=2),
        )
        # Due today lead
        Lead.objects.create(
            name="Due Today Lead",
            phone="9825600003",
            assigned_to=sales_user,
            status="Interested",
            next_followup_at=now,
        )

        # Tab: due_today
        res_today = client.get('/api/leads/?tab=due_today')
        assert res_today.status_code == 200
        items_today = res_today.json()
        if isinstance(items_today, dict):
            items_today = items_today.get('results', [])
        names = [item['name'] for item in items_today]
        assert "Due Today Lead" in names

        # Tab: overdue
        res_overdue = client.get('/api/leads/?tab=overdue')
        assert res_overdue.status_code == 200
        items_od = res_overdue.json()
        if isinstance(items_od, dict):
            items_od = items_od.get('results', [])
        names_od = [item['name'] for item in items_od]
        assert "Overdue Lead" in names_od
