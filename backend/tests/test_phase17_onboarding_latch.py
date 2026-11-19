import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import User, UserTourState, UserOnboardingState
from leads.models import Lead
from quotes.models import Quote


@pytest.mark.django_db
class TestOnboardingCompletionLatch:
    def setup_method(self):
        self.client = APIClient()
        self.sales_user = User.objects.create_user(
            username="latch_sales_user",
            password="TestPassword123!",
            role=User.Role.SALESPERSON,
        )
        self.surveyor_user = User.objects.create_user(
            username="latch_surveyor_user",
            password="TestPassword123!",
            role=User.Role.SURVEYOR,
        )
        self.admin_user = User.objects.create_user(
            username="latch_admin_user",
            password="TestPassword123!",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def test_new_user_initial_onboarding_state(self):
        self.client.force_authenticate(user=self.sales_user)
        res = self.client.get('/api/me/onboarding/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["visible"] is True
        assert len(data["items"]) == 4
        assert all(item["done"] is False for item in data["items"])
        assert data["completed_at"] is None
        assert data["dismissed_at"] is None

    def test_role_specific_item_lists(self):
        # Surveyor gets 3 role items: tour, surveys, tour_center
        self.client.force_authenticate(user=self.surveyor_user)
        res = self.client.get('/api/me/onboarding/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        item_ids = [i["id"] for i in data["items"]]
        assert item_ids == ["tour", "surveys", "tour_center"]

    def test_item_progression_and_one_way_completion_latch(self):
        self.client.force_authenticate(user=self.sales_user)

        # 1. Tick tour
        res = self.client.post('/api/me/onboarding/', {"action": "event", "event": "tour"})
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["visible"] is True
        assert any(i["id"] == "tour" and i["done"] is True for i in data["items"])
        assert data["completed_at"] is None

        # 2. Tick leads
        res = self.client.post('/api/me/onboarding/', {"action": "event", "event": "leads"})
        assert res.json()["visible"] is True

        # 3. Tick quote
        res = self.client.post('/api/me/onboarding/', {"action": "event", "event": "quote"})
        assert res.json()["visible"] is True

        # 4. Tick final item (tour_center) -> completes onboarding!
        res = self.client.post('/api/me/onboarding/', {"action": "event", "event": "tour_center"})
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["visible"] is False
        assert data["completed_at"] is not None

        # Verify state in DB
        state = UserOnboardingState.objects.get(user=self.sales_user)
        assert state.completed_at is not None
        assert state.is_latched() is True

        # Subsequent GET requests MUST return visible=False and empty items
        get_res = self.client.get('/api/me/onboarding/')
        get_data = get_res.json()
        assert get_data["visible"] is False
        assert get_data["items"] == []
        assert get_data["completed_at"] is not None

    def test_latch_persists_even_after_data_deletion_or_tour_reset(self):
        self.client.force_authenticate(user=self.sales_user)
        # Directly latch completion
        self.client.post('/api/me/onboarding/', {"action": "complete"})
        assert UserOnboardingState.objects.get(user=self.sales_user).is_latched() is True

        # Admin resets product tour
        self.client.force_authenticate(user=self.admin_user)
        tour_reset_res = self.client.post('/api/me/tour/', {"all": True})
        assert tour_reset_res.status_code == status.HTTP_200_OK

        # Authenticate back as sales user: onboarding latch MUST NOT be broken!
        self.client.force_authenticate(user=self.sales_user)
        res = self.client.get('/api/me/onboarding/')
        data = res.json()
        assert data["visible"] is False
        assert data["items"] == []
        assert data["completed_at"] is not None

    def test_dismiss_action_latches_permanently(self):
        self.client.force_authenticate(user=self.sales_user)
        res = self.client.post('/api/me/onboarding/', {"action": "dismiss"})
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["visible"] is False
        assert data["dismissed_at"] is not None
        assert data["items"] == []

        # Persistent across reloads
        res2 = self.client.get('/api/me/onboarding/')
        assert res2.json()["visible"] is False
        assert res2.json()["items"] == []

    def test_collapse_toggle_persists_without_latching(self):
        self.client.force_authenticate(user=self.sales_user)
        res = self.client.post('/api/me/onboarding/', {"action": "collapse", "is_collapsed": True})
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["is_collapsed"] is True

        # Still visible
        res2 = self.client.get('/api/me/onboarding/')
        assert res2.json()["visible"] is True
        assert res2.json()["is_collapsed"] is True
        assert res2.json()["completed_at"] is None
