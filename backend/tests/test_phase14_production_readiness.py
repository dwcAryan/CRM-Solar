import io
import logging

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from config.logging_filters import SensitiveDataFilter
from leads.models import Lead
from masters.models import Region


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def region_in(db):
    return Region.objects.get_or_create(
        code="IN",
        defaults={
            "name": "India",
            "currency": "INR",
            "currency_symbol": "₹",
            "default_timezone": "Asia/Kolkata",
        },
    )[0]


@pytest.mark.django_db
class TestPhase14ProductionReadiness:
    def test_health_check_endpoint(self, api_client):
        """Verifies /api/health/ returns HTTP 200 with ready=True and database connected."""
        res = api_client.get("/api/health/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["ready"] is True
        assert data["database"] == "connected"
        assert data["migrations"] == "up_to_date"
        assert "environment" in data

    @override_settings(APP_ENV="production")
    def test_seed_demo_refuses_in_production(self):
        """Verifies seed_demo command refuses execution when APP_ENV=production."""
        with pytest.raises(CommandError, match="cannot be run in production"):
            call_command("seed_demo")

    def test_remove_demo_data_command(self, region_in):
        """Verifies remove_demo_data purges all demo users and demo data."""
        # Create a demo user
        demo_user = User.objects.create_user(
            username="demo_temp_user",
            password="DemoPassword123!",
            role=User.Role.SALESPERSON,
            is_demo=True,
            default_region=region_in,
        )
        # Create a real user
        User.objects.create_user(
            username="real_active_user",
            password="RealPassword123!",
            role=User.Role.SALESPERSON,
            is_demo=False,
            default_region=region_in,
        )
        # Create a lead assigned to demo user
        Lead.objects.create(
            name="Demo Lead",
            phone="+919800011111",
            phone_e164="+919800011111",
            region=region_in,
            assigned_to=demo_user,
        )

        out = io.StringIO()
        call_command("remove_demo_data", force=True, stdout=out)
        output = out.getvalue()
        assert "All demo users and demo data successfully removed from database!" in output

        # Assert demo user is gone, real user remains
        assert not User.objects.filter(username="demo_temp_user").exists()
        assert User.objects.filter(username="real_active_user").exists()

    def test_password_change_view_and_must_change_flag(self, api_client, region_in):
        """Verifies password change view enforces complexity and clears must_change_password."""
        user = User.objects.create_user(
            username="new_staff_user",
            password="InitialPass123!",
            role=User.Role.SALESPERSON,
            is_demo=False,
            must_change_password=True,
            default_region=region_in,
        )
        api_client.force_authenticate(user=user)

        # 1. Weak password rejected (< 10 chars)
        res_weak = api_client.post("/api/auth/change-password/", {
            "current_password": "InitialPass123!",
            "new_password": "Short1!",
        })
        assert res_weak.status_code == status.HTTP_400_BAD_REQUEST

        # 2. Strong password accepted
        res_strong = api_client.post("/api/auth/change-password/", {
            "current_password": "InitialPass123!",
            "new_password": "BrandNewSecurePassword2026!",
        })
        assert res_strong.status_code == status.HTTP_200_OK

        user.refresh_from_db()
        assert user.must_change_password is False
        assert user.check_password("BrandNewSecurePassword2026!")

    def test_sensitive_data_logging_filter(self):
        """Verifies SensitiveDataFilter scrubs tokens, passwords, and customer phone numbers."""
        filter_instance = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg='User login attempt for customer +919876543210 with password="SecretPassword123" and token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy',
            args=(),
            exc_info=None,
        )
        filter_instance.filter(record)
        scrubbed = record.getMessage()

        assert "SecretPassword123" not in scrubbed
        assert "[PHONE_REDACTED]" in scrubbed
        assert "[REDACTED]" in scrubbed
