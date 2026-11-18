import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from accounts.permissions import PERMISSION_MATRIX, can, get_user_permissions
from activities.models import Activity
from leads.models import AuditLog, Lead
from masters.models import LostReason, Outcome, Region
from quotes.models import Quote
from surveys.models import Survey
from tests.factories import (
    ActivityFactory,
    LeadFactory,
    QuoteFactory,
    RegionFactory,
    SurveyFactory,
    UserFactory,
)


@pytest.fixture
def region_in(db):
    return RegionFactory(code='IN', name='India', currency='INR', phone_country_code='+91')


@pytest.fixture
def region_au(db):
    return RegionFactory(code='AU', name='Australia', currency='AUD', phone_country_code='+61')


@pytest.fixture
def admin_user(db, region_in, region_au):
    user = UserFactory(username='admin_test', role=User.Role.ADMIN, is_staff=True)
    user.allowed_regions.set([region_in, region_au])
    return user


@pytest.fixture
def manager_user(db, region_in):
    user = UserFactory(username='mgr_in_test', role=User.Role.MANAGER)
    user.allowed_regions.set([region_in])
    return user


@pytest.fixture
def salesperson_user(db, region_in):
    user = UserFactory(username='sales_in_test', role=User.Role.SALESPERSON)
    user.allowed_regions.set([region_in])
    return user


@pytest.fixture
def other_salesperson_user(db, region_in):
    user = UserFactory(username='sales_other_test', role=User.Role.SALESPERSON)
    user.allowed_regions.set([region_in])
    return user


@pytest.fixture
def surveyor_user(db, region_in):
    user = UserFactory(username='surveyor_in_test', role=User.Role.SURVEYOR)
    user.allowed_regions.set([region_in])
    return user


@pytest.mark.django_db
class TestCentralRBACPermissionMatrix:
    """Tests evaluating central permission matrix rules and helper can()."""

    def test_permission_matrix_integrity(self):
        """Ensure all permissions in PERMISSION_MATRIX have entries for all 4 roles."""
        expected_roles = {"admin", "manager", "salesperson", "surveyor"}
        for perm_key, role_map in PERMISSION_MATRIX.items():
            assert set(role_map.keys()) == expected_roles, f"Permission {perm_key} missing roles"

    def test_get_user_permissions(self, admin_user, manager_user, salesperson_user, surveyor_user):
        """Verifies get_user_permissions returns accurate active keys."""
        admin_perms = get_user_permissions(admin_user)
        mgr_perms = get_user_permissions(manager_user)
        sales_perms = get_user_permissions(salesperson_user)
        survey_perms = get_user_permissions(surveyor_user)

        assert "user.manage" in admin_perms
        assert "user.manage" not in mgr_perms
        assert "user.manage" not in sales_perms

        assert "lead.assign" in admin_perms
        assert "lead.assign" in mgr_perms
        assert "lead.assign" not in sales_perms
        assert "lead.assign" not in survey_perms

        assert "lead.view" in sales_perms
        assert "lead.view" not in survey_perms


@pytest.mark.django_db
class TestRoleWorkAreasAndAccess:
    """Verifies strict role boundary enforcement across API endpoints."""

    def test_surveyor_cannot_access_leads_list(self, surveyor_user, region_in):
        """Surveyor gets 403 on /api/leads/ directly."""
        client = APIClient()
        client.force_authenticate(user=surveyor_user)

        res = client.get('/api/leads/')
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_surveyor_accesses_my_surveys_only(self, surveyor_user, salesperson_user, region_in):
        """Surveyor accesses /api/surveys/my-surveys/ and only sees surveys assigned to them."""
        lead = LeadFactory(region=region_in, assigned_to=salesperson_user)
        s1 = SurveyFactory(lead=lead, surveyor=surveyor_user, scheduled_at=timezone.now())
        s2 = SurveyFactory(lead=lead, surveyor=None, scheduled_at=timezone.now())

        client = APIClient()
        client.force_authenticate(user=surveyor_user)

        res = client.get('/api/surveys/my-surveys/?filter=today')
        assert res.status_code == status.HTTP_200_OK
        survey_ids = [s['id'] for s in res.data]
        assert s1.id in survey_ids
        assert s2.id not in survey_ids

    def test_surveyor_data_stripping(self, surveyor_user, salesperson_user, region_in):
        """Surveyor responses have sensitive fields stripped (remarks, prices, etc.)."""
        lead = LeadFactory(region=region_in, assigned_to=salesperson_user, remark="Customer is wealthy, push 10kW")
        survey = SurveyFactory(lead=lead, surveyor=surveyor_user, scheduled_at=timezone.now(), remark="Confidential internal note")

        client = APIClient()
        client.force_authenticate(user=surveyor_user)

        res = client.get(f'/api/surveys/{survey.id}/')
        assert res.status_code == status.HTTP_200_OK
        # Field stripping check: remark must not be exposed to surveyor
        assert 'remark' not in res.data or res.data.get('remark') is None

    def test_salesperson_cannot_assign_or_reassign(self, salesperson_user, other_salesperson_user, region_in):
        """Salesperson cannot assign or reassign leads."""
        lead = LeadFactory(region=region_in, assigned_to=salesperson_user)
        client = APIClient()
        client.force_authenticate(user=salesperson_user)

        res = client.post(f'/api/leads/{lead.id}/assign/', {'assigned_to_id': other_salesperson_user.id})
        assert res.status_code == status.HTTP_403_FORBIDDEN

        res_bulk = client.post('/api/leads/bulk-assign/', {
            'lead_ids': [lead.id],
            'assigned_to_id': other_salesperson_user.id
        })
        assert res_bulk.status_code == status.HTTP_403_FORBIDDEN

    def test_salesperson_cannot_export_or_import(self, salesperson_user):
        """Salesperson cannot export or import leads."""
        client = APIClient()
        client.force_authenticate(user=salesperson_user)

        assert client.get('/api/leads/export-csv/').status_code == status.HTTP_403_FORBIDDEN
        assert client.get('/api/leads/import-sample-csv/').status_code == status.HTTP_403_FORBIDDEN
        assert client.post('/api/leads/preview-csv/').status_code == status.HTTP_403_FORBIDDEN

    def test_salesperson_lost_requires_approval(self, salesperson_user, manager_user, region_in):
        """When salesperson logs outcome leading to Lost, lead status goes to LOST_APPROVAL_PENDING."""
        lead = LeadFactory(region=region_in, assigned_to=salesperson_user)
        lost_reason = LostReason.objects.create(name='Competitor price lower')
        outcome = Outcome.objects.create(
            stage=Outcome.Stage.CALL,
            name='Customer rejects deal',
            default_status=Lead.Status.LOST,
            requires_lost_reason=True,
        )

        client = APIClient()
        client.force_authenticate(user=salesperson_user)

        res = client.post(f'/api/leads/{lead.id}/log-activity/', {
            'type': Activity.Type.CALL,
            'outcome_id': outcome.id,
            'lost_reason_id': lost_reason.id,
            'notes': 'Customer said price too high',
        })
        assert res.status_code == status.HTTP_200_OK

        lead.refresh_from_db()
        assert lead.status == Lead.Status.LOST_APPROVAL_PENDING
        assert lead.lost_pending_reason == lost_reason
        assert lead.lost_pending_notes == 'Customer said price too high'

        # Manager reviews lost approvals queue and approves
        client.force_authenticate(user=manager_user)
        res_queue = client.get('/api/leads/lost-approvals/')
        assert res_queue.status_code == status.HTTP_200_OK
        data_items = res_queue.data if isinstance(res_queue.data, list) else res_queue.data.get('results', [])
        ids = [item['id'] for item in data_items]
        assert lead.id in ids

        res_approve = client.post(f'/api/leads/{lead.id}/approve-lost/', {'notes': 'Agreed, deal is lost.'})
        assert res_approve.status_code == status.HTTP_200_OK

        lead.refresh_from_db()
        assert lead.status == Lead.Status.LOST
        assert lead.lost_reason == lost_reason

    def test_manager_attention_queues(self, manager_user, salesperson_user, region_in):
        """Manager has access to unassigned queue and lost approvals queue."""
        unassigned_lead = LeadFactory(region=region_in, assigned_to=None)
        client = APIClient()
        client.force_authenticate(user=manager_user)

        res_unassigned = client.get('/api/leads/unassigned/')
        assert res_unassigned.status_code == status.HTTP_200_OK
        unassigned_list = res_unassigned.data if isinstance(res_unassigned.data, list) else res_unassigned.data.get('results', [])
        unassigned_ids = [l['id'] for l in unassigned_list]
        assert unassigned_lead.id in unassigned_ids

    def test_activity_immutability_and_correction_notes(self, admin_user, salesperson_user, region_in):
        """Activities are append-only. Only admin can append correction note."""
        lead = LeadFactory(region=region_in, assigned_to=salesperson_user)
        activity = ActivityFactory(lead=lead, created_by=salesperson_user)

        client = APIClient()
        client.force_authenticate(user=salesperson_user)

        # Update / Delete blocked
        assert client.patch(f'/api/activities/{activity.id}/', {'notes': 'Edited'}).status_code == status.HTTP_403_FORBIDDEN
        assert client.delete(f'/api/activities/{activity.id}/').status_code == status.HTTP_403_FORBIDDEN

        # Salesperson cannot add correction note
        assert client.post(f'/api/activities/{activity.id}/add-correction/', {'admin_correction_note': 'Wrong'}).status_code == status.HTTP_403_FORBIDDEN

        # Admin CAN add correction note
        client.force_authenticate(user=admin_user)
        res_corr = client.post(f'/api/activities/{activity.id}/add-correction/', {
            'admin_correction_note': 'Customer confirmed this was a typo'
        })
        assert res_corr.status_code == status.HTTP_200_OK
        activity.refresh_from_db()
        assert activity.admin_correction_note == 'Customer confirmed this was a typo'
        assert activity.correction_added_by == admin_user

    def test_me_endpoint_privilege_escalation_block(self, salesperson_user):
        """PATCH /api/me/ rejects privilege escalation fields."""
        client = APIClient()
        client.force_authenticate(user=salesperson_user)

        res = client.patch('/api/me/', {'role': 'admin'})
        assert res.status_code == status.HTTP_403_FORBIDDEN

        res_staff = client.patch('/api/me/', {'is_staff': True})
        assert res_staff.status_code == status.HTTP_403_FORBIDDEN

        # Allowed update
        res_ok = client.patch('/api/me/', {'first_name': 'NewName'})
        assert res_ok.status_code == status.HTTP_200_OK
        salesperson_user.refresh_from_db()
        assert salesperson_user.first_name == 'NewName'

    def test_soft_delete_with_audit_reason(self, admin_user, manager_user, salesperson_user, region_in):
        """Only admin can delete lead; requires mandatory reason; soft-deleted leads excluded from regular queries."""
        lead = LeadFactory(region=region_in, assigned_to=salesperson_user)

        client = APIClient()
        client.force_authenticate(user=manager_user)
        # Manager delete refused
        assert client.delete(f'/api/leads/{lead.id}/').status_code == status.HTTP_403_FORBIDDEN

        # Admin delete without reason refused
        client.force_authenticate(user=admin_user)
        res_no_reason = client.delete(f'/api/leads/{lead.id}/')
        assert res_no_reason.status_code == status.HTTP_400_BAD_REQUEST

        # Admin delete with reason succeeds
        res_delete = client.delete(f'/api/leads/{lead.id}/', {'reason': 'Customer requested data erasure under GDPR'})
        assert res_delete.status_code == status.HTTP_200_OK

        lead.refresh_from_db()
        assert lead.is_deleted is True
        assert lead.deleted_reason == 'Customer requested data erasure under GDPR'
        assert lead.deleted_by == admin_user

        # Soft-deleted lead hidden from leads list
        res_list = client.get('/api/leads/')
        data_list = res_list.data if isinstance(res_list.data, list) else res_list.data.get('results', [])
        lead_ids = [l['id'] for l in data_list]
        assert lead.id not in lead_ids


@pytest.mark.django_db
class TestEndpointRBACParametrized:
    """Parametrized matrix check verifying that unauthorized roles are denied access across endpoints."""

    @pytest.mark.parametrize("endpoint,method,role,expected_status", [
        # Anonymous users
        ("/api/leads/", "get", "anon", status.HTTP_401_UNAUTHORIZED),
        ("/api/surveys/", "get", "anon", status.HTTP_401_UNAUTHORIZED),
        ("/api/quotes/", "get", "anon", status.HTTP_401_UNAUTHORIZED),
        ("/api/roles-matrix/", "get", "anon", status.HTTP_401_UNAUTHORIZED),

        # Surveyor role restrictions
        ("/api/leads/", "get", "surveyor", status.HTTP_403_FORBIDDEN),
        ("/api/quotes/", "get", "surveyor", status.HTTP_403_FORBIDDEN),
        ("/api/activities/", "get", "surveyor", status.HTTP_403_FORBIDDEN),
        ("/api/roles-matrix/", "get", "surveyor", status.HTTP_403_FORBIDDEN),

        # Salesperson role restrictions
        ("/api/leads/unassigned/", "get", "salesperson", status.HTTP_403_FORBIDDEN),
        ("/api/leads/lost-approvals/", "get", "salesperson", status.HTTP_403_FORBIDDEN),
        ("/api/leads/export-csv/", "get", "salesperson", status.HTTP_403_FORBIDDEN),
        ("/api/roles-matrix/", "get", "salesperson", status.HTTP_403_FORBIDDEN),

        # Manager allowed endpoints
        ("/api/leads/unassigned/", "get", "manager", status.HTTP_200_OK),
        ("/api/leads/lost-approvals/", "get", "manager", status.HTTP_200_OK),
        ("/api/roles-matrix/", "get", "manager", status.HTTP_200_OK),

        # Admin allowed endpoints
        ("/api/roles-matrix/", "get", "admin", status.HTTP_200_OK),
        ("/api/leads/unassigned/", "get", "admin", status.HTTP_200_OK),
    ])
    def test_parametrized_role_access(
        self, endpoint, method, role, expected_status,
        admin_user, manager_user, salesperson_user, surveyor_user
    ):
        client = APIClient()
        role_map = {
            "admin": admin_user,
            "manager": manager_user,
            "salesperson": salesperson_user,
            "surveyor": surveyor_user,
        }
        user = role_map.get(role)
        if user:
            client.force_authenticate(user=user)

        client_method = getattr(client, method.lower())
        res = client_method(endpoint)
        assert res.status_code == expected_status, f"Role {role} {method.upper()} {endpoint} expected {expected_status}, got {res.status_code}"
