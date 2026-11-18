from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from activities.models import Activity
from leads.models import Lead, LeadStatusHistory
from leads.services import process_log_activity
from masters.models import LostReason, Outcome
from quotes.models import Quote


@pytest.fixture(autouse=True)
def setup_master_data(db):
    call_command('seed_masters')


@pytest.fixture
def admin_user(db):
    user, _ = User.objects.get_or_create(
        username='test_admin',
        defaults={'email': 'admin@test.com', 'role': User.Role.ADMIN, 'is_staff': True, 'is_superuser': True}
    )
    user.set_password('TestPass123!')
    user.save()
    return user


@pytest.fixture
def manager_user(db):
    user, _ = User.objects.get_or_create(
        username='test_manager',
        defaults={'email': 'manager@test.com', 'role': User.Role.MANAGER, 'is_staff': True}
    )
    user.set_password('TestPass123!')
    user.save()
    return user


@pytest.fixture
def salesperson_user(db):
    user, _ = User.objects.get_or_create(
        username='test_sales1',
        defaults={'email': 'sales1@test.com', 'role': User.Role.SALESPERSON}
    )
    user.set_password('TestPass123!')
    user.save()
    return user


@pytest.fixture
def other_salesperson(db):
    user, _ = User.objects.get_or_create(
        username='test_sales2',
        defaults={'email': 'sales2@test.com', 'role': User.Role.SALESPERSON}
    )
    user.set_password('TestPass123!')
    user.save()
    return user


@pytest.fixture
def surveyor_user(db):
    user, _ = User.objects.get_or_create(
        username='test_surveyor',
        defaults={'email': 'surveyor@test.com', 'role': User.Role.SURVEYOR}
    )
    user.set_password('TestPass123!')
    user.save()
    return user


@pytest.fixture
def sample_lead(db, salesperson_user):
    return Lead.objects.create(
        name='Aarav Mehta',
        phone='9825099999',
        city='Ahmedabad',
        status=Lead.Status.NEW,
        assigned_to=salesperson_user,
    )


@pytest.mark.django_db
class TestPhase3BusinessLogic:

    def test_log_activity_defaults(self, sample_lead, salesperson_user):
        """1. Outcome defaults: status, next action, followup date = now + default days."""
        outcome = Outcome.objects.get(stage=Outcome.Stage.CALL, name='Interested, wants more information')

        activity, updated_lead = process_log_activity(
            lead=sample_lead,
            user=salesperson_user,
            data={
                'type': Activity.Type.CALL,
                'outcome_id': outcome.id,
                'notes': 'Spoke with customer, very interested in 5kW system.',
            }
        )

        assert activity.status_after == 'Interested'
        assert updated_lead.status == 'Interested'
        assert updated_lead.next_action == outcome.default_next_action
        assert updated_lead.next_followup_at is not None
        # Should be roughly 2 days in the future
        diff_days = (updated_lead.next_followup_at - timezone.now()).total_seconds() / 86400
        assert 1.8 < diff_days < 2.2

    def test_missing_date_validation(self, sample_lead, salesperson_user):
        """Validation: next_followup_at is required unless resulting status is terminal."""
        outcome = Outcome.objects.get(stage=Outcome.Stage.CALL, name='Customer asks to call later')

        # Outcome requires manual date and has no default days
        with pytest.raises(ValidationError):
            process_log_activity(
                lead=sample_lead,
                user=salesperson_user,
                data={
                    'type': Activity.Type.CALL,
                    'outcome_id': outcome.id,
                    'notes': 'Wants callback',
                    # next_followup_at omitted
                }
            )

        # But terminal status (e.g. Wrong or invalid number -> Invalid contact) allows empty date
        invalid_outcome = Outcome.objects.get(stage=Outcome.Stage.CALL, name='Wrong or invalid number')
        _, updated_lead = process_log_activity(
            lead=sample_lead,
            user=salesperson_user,
            data={
                'type': Activity.Type.CALL,
                'outcome_id': invalid_outcome.id,
                'notes': 'Number is dead',
            }
        )
        assert updated_lead.status == Lead.Status.INVALID_CONTACT
        assert updated_lead.next_followup_at is None

    def test_status_history_recording(self, sample_lead, salesperson_user):
        """3. Status transitions must record LeadStatusHistory."""
        outcome = Outcome.objects.get(stage=Outcome.Stage.CALL, name='Not the decision maker')

        assert LeadStatusHistory.objects.filter(lead=sample_lead).count() == 0

        process_log_activity(
            lead=sample_lead,
            user=salesperson_user,
            data={
                'type': Activity.Type.CALL,
                'outcome_id': outcome.id,
                'notes': 'Spoke with son, father makes decisions.',
            }
        )

        history = LeadStatusHistory.objects.filter(lead=sample_lead).first()
        assert history is not None
        assert history.old_status == Lead.Status.NEW
        assert history.new_status == Lead.Status.FOLLOW_UP
        assert history.changed_by == salesperson_user

    def test_retry_rule_through_unreachable_and_lost(self, sample_lead, salesperson_user):
        """2. Retry rule for 'No answer' through Unreachable and Lost."""
        outcome_no_answer = Outcome.objects.get(stage=Outcome.Stage.CALL, name='No answer')

        # Attempt 1: same day, a few hours later
        _, lead = process_log_activity(
            lead=sample_lead,
            user=salesperson_user,
            data={'type': Activity.Type.CALL, 'outcome_id': outcome_no_answer.id}
        )
        assert lead.attempt_count == 1
        assert lead.status == Lead.Status.ATTEMPTING_CONTACT
        assert (lead.next_followup_at - timezone.now()).total_seconds() < 86400  # same day

        # Attempt 2: next day
        _, lead = process_log_activity(
            lead=lead,
            user=salesperson_user,
            data={'type': Activity.Type.CALL, 'outcome_id': outcome_no_answer.id}
        )
        assert lead.attempt_count == 2
        assert lead.status == Lead.Status.ATTEMPTING_CONTACT

        # Attempts 3 and 4
        _, lead = process_log_activity(
            lead=lead,
            user=salesperson_user,
            data={'type': Activity.Type.CALL, 'outcome_id': outcome_no_answer.id}
        )
        assert lead.attempt_count == 3
        _, lead = process_log_activity(
            lead=lead,
            user=salesperson_user,
            data={'type': Activity.Type.CALL, 'outcome_id': outcome_no_answer.id}
        )
        assert lead.attempt_count == 4

        # Attempt 5: reaches MAX_CALL_ATTEMPTS_BEFORE_UNREACHABLE (5) -> Unreachable in 14 days
        _, lead = process_log_activity(
            lead=lead,
            user=salesperson_user,
            data={'type': Activity.Type.CALL, 'outcome_id': outcome_no_answer.id}
        )
        assert lead.attempt_count == 5
        assert lead.status == Lead.Status.UNREACHABLE
        diff_days = (lead.next_followup_at - timezone.now()).total_seconds() / 86400
        assert 13 < diff_days < 15

        # While Unreachable, another "No answer" logged by salesperson -> Lost approval pending with reason "no response"
        _, lead = process_log_activity(
            lead=lead,
            user=salesperson_user,
            data={'type': Activity.Type.CALL, 'outcome_id': outcome_no_answer.id}
        )
        assert lead.status == Lead.Status.LOST_APPROVAL_PENDING
        assert lead.lost_pending_reason.name.lower() == 'no response'
        assert lead.next_followup_at is not None

    def test_answered_call_resets_attempt_count(self, sample_lead, salesperson_user):
        """Call answered resets attempt_count to 0."""
        outcome_no_answer = Outcome.objects.get(stage=Outcome.Stage.CALL, name='No answer')
        _, lead = process_log_activity(
            lead=sample_lead,
            user=salesperson_user,
            data={'type': Activity.Type.CALL, 'outcome_id': outcome_no_answer.id}
        )
        assert lead.attempt_count == 1

        # Customer answers and asks to call later
        outcome_answered = Outcome.objects.get(stage=Outcome.Stage.CALL, name='Customer asks to call later')
        future_time = timezone.now() + timedelta(days=1)
        _, lead = process_log_activity(
            lead=lead,
            user=salesperson_user,
            data={
                'type': Activity.Type.CALL,
                'outcome_id': outcome_answered.id,
                'next_followup_at': future_time,
            }
        )
        assert lead.attempt_count == 0

    def test_do_not_contact_blocking(self, sample_lead, salesperson_user):
        """Do not contact blocks further call or whatsapp activity."""
        dnc_outcome = Outcome.objects.get(stage=Outcome.Stage.CALL, name='Asked not to be called again')

        _, lead = process_log_activity(
            lead=sample_lead,
            user=salesperson_user,
            data={'type': Activity.Type.CALL, 'outcome_id': dnc_outcome.id}
        )
        assert lead.do_not_contact is True
        assert lead.status == Lead.Status.DO_NOT_CONTACT

        # Attempt to make another call -> must be blocked
        outcome_info = Outcome.objects.get(stage=Outcome.Stage.CALL, name='Interested, wants more information')
        with pytest.raises(ValidationError):
            process_log_activity(
                lead=lead,
                user=salesperson_user,
                data={'type': Activity.Type.CALL, 'outcome_id': outcome_info.id}
            )

    def test_duplicate_detection_by_phone(self, db, salesperson_user):
        """5. Duplicate phone normalization and detection."""
        client = APIClient()
        client.force_authenticate(user=salesperson_user)

        # Create primary lead
        response = client.post('/api/leads/', {
            'name': 'Bhavin Patel',
            'phone': '+91 98251-12345',
            'city': 'Surat',
        })
        assert response.status_code == status.HTTP_201_CREATED
        primary_id = response.data['id']

        # Attempt to create duplicate with formatted/local number
        response2 = client.post('/api/leads/', {
            'name': 'Bhavin P. Duplicate',
            'phone': '098251 12345',
            'city': 'Surat',
        })
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert 'duplicate' in response2.data
        assert int(response2.data['existing_lead']['id']) == primary_id

    def test_merge_endpoint(self, db, salesperson_user, manager_user):
        """Merge a duplicate lead into a primary lead."""
        primary = Lead.objects.create(name='Primary Lead', phone='9825211111', status=Lead.Status.NEW, assigned_to=salesperson_user)
        duplicate = Lead.objects.create(name='Duplicate Lead', phone='9825222222', status=Lead.Status.NEW, assigned_to=salesperson_user)

        client = APIClient()
        # Salesperson cannot merge leads
        client.force_authenticate(user=salesperson_user)
        res_sales = client.post(f'/api/leads/{duplicate.id}/merge/', {
            'target_lead_id': primary.id,
            'note': 'Attempt by salesperson',
        })
        assert res_sales.status_code == status.HTTP_403_FORBIDDEN

        # Manager CAN merge leads
        client.force_authenticate(user=manager_user)
        response = client.post(f'/api/leads/{duplicate.id}/merge/', {
            'target_lead_id': primary.id,
            'note': 'Customer confirmed same person on different number.',
        })
        assert response.status_code == status.HTTP_200_OK

        duplicate.refresh_from_db()
        assert duplicate.status == Lead.Status.MERGED
        assert duplicate.next_followup_at is None

    def test_role_permissions_and_marking_lost(self, sample_lead, salesperson_user, manager_user, other_salesperson):
        """Role permissions: salesperson only sees own; lost restriction."""
        client = APIClient()

        # Salesperson tries to access lead assigned to another salesperson
        sample_lead.assigned_to = other_salesperson
        sample_lead.save()

        client.force_authenticate(user=salesperson_user)
        response = client.get(f'/api/leads/{sample_lead.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Manager can view it
        client.force_authenticate(user=manager_user)
        response = client.get(f'/api/leads/{sample_lead.id}/')
        assert response.status_code == status.HTTP_200_OK

        # Salesperson cannot mark lead directly as Lost (submits for Lost approval)
        lost_outcome = Outcome.objects.get(stage=Outcome.Stage.CALL, name='Not interested at all')
        lost_reason = LostReason.objects.first()

        sample_lead.assigned_to = salesperson_user
        sample_lead.save()

        # Salesperson logging Lost outcome routes to LOST_APPROVAL_PENDING
        _, pending_lead = process_log_activity(
            lead=sample_lead,
            user=salesperson_user,
            data={
                'type': Activity.Type.CALL,
                'outcome_id': lost_outcome.id,
                'lost_reason_id': lost_reason.id,
            }
        )
        assert pending_lead.status == Lead.Status.LOST_APPROVAL_PENDING
        assert pending_lead.lost_pending_reason == lost_reason

        # Salesperson cannot manually set status (manual_status endpoint is restricted)
        client.force_authenticate(user=salesperson_user)
        man_res = client.post(f'/api/leads/{sample_lead.id}/manual-status/', {'status': Lead.Status.LOST})
        assert man_res.status_code == status.HTTP_403_FORBIDDEN

        # Manager CAN mark as Lost
        _, updated_lead = process_log_activity(
            lead=sample_lead,
            user=manager_user,
            data={
                'type': Activity.Type.CALL,
                'outcome_id': lost_outcome.id,
                'lost_reason_id': lost_reason.id,
            }
        )
        assert updated_lead.status == Lead.Status.LOST
        assert updated_lead.lost_reason == lost_reason

    def test_survey_transitions(self, sample_lead, admin_user, surveyor_user):
        """7. Survey booking, rescheduling, missed, and completion with site suitability."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        scheduled_time = timezone.now() + timedelta(days=2)

        # Book
        res = client.post('/api/surveys/book/', {
            'lead_id': sample_lead.id,
            'scheduled_at': scheduled_time.isoformat(),
            'surveyor_id': surveyor_user.id,
            'notes': 'Booked site visit',
        })
        assert res.status_code == status.HTTP_201_CREATED
        survey_id = res.data['id']

        sample_lead.refresh_from_db()
        assert sample_lead.status == Lead.Status.SURVEY_SCHEDULED

        # Reschedule
        new_time = timezone.now() + timedelta(days=4)
        res = client.post(f'/api/surveys/{survey_id}/reschedule/', {
            'scheduled_at': new_time.isoformat(),
            'notes': 'Customer requested delay',
        })
        assert res.status_code == status.HTTP_200_OK
        assert res.data['reschedule_count'] == 1

        sample_lead.refresh_from_db()
        assert sample_lead.status == Lead.Status.SURVEY_RESCHEDULED

        # Mark Done & Suitable -> Design Pending
        res = client.post(f'/api/surveys/{survey_id}/mark-done/', {
            'site_suitable': True,
            'notes': 'Good terrace space, 8kW possible without shadow',
        })
        assert res.status_code == status.HTTP_200_OK

        sample_lead.refresh_from_db()
        assert sample_lead.status == Lead.Status.DESIGN_PENDING
        assert sample_lead.next_action == "Prepare the design and quotation"

    def test_quote_versioning_and_won(self, sample_lead, admin_user):
        """8. Quote creation, sent, revision with version increment, accept to Won."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Create v1
        res = client.post('/api/quotes/', {
            'lead_id': sample_lead.id,
            'system_size_kw': 5.0,
            'brand': 'Waaree 540W Mono PERC',
            'price': 280000.00,
            'subsidy_amount': 78000.00,
        })
        assert res.status_code == status.HTTP_201_CREATED
        quote_v1_id = res.data['id']
        assert res.data['version'] == 1

        # Mark sent
        res = client.post(f'/api/quotes/{quote_v1_id}/mark-sent/')
        assert res.status_code == status.HTTP_200_OK
        sample_lead.refresh_from_db()
        assert sample_lead.status == Lead.Status.QUOTE_SENT

        # Revise -> creates v2, v1 preserved
        res = client.post(f'/api/quotes/{quote_v1_id}/revise/', {
            'system_size_kw': 6.0,
            'brand': 'Waaree 540W Mono PERC + Sungrow',
            'price': 320000.00,
            'notes': 'Upgraded to 6kW on customer request',
        })
        assert res.status_code == status.HTTP_201_CREATED
        quote_v2_id = res.data['id']
        assert res.data['version'] == 2

        # Verify v1 still exists
        v1 = Quote.objects.get(id=quote_v1_id)
        assert v1.status == Quote.Status.REVISED

        # Deleting old quote must fail
        with pytest.raises(ValidationError):
            v1.delete()

        # Customer accepts quote v2 -> Won
        res = client.post(f'/api/quotes/{quote_v2_id}/accept/')
        assert res.status_code == status.HTTP_200_OK

        sample_lead.refresh_from_db()
        assert sample_lead.status == Lead.Status.WON
        assert sample_lead.won_at is not None
        assert sample_lead.next_followup_at is None
