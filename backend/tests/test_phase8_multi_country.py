import json
import zoneinfo
from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from activities.models import Activity
from leads.models import (
    AuditLog,
    Lead,
    LeadStatusHistory,
)
from leads.phone_utils import normalize_phone_number
from leads.privacy_service import anonymize_lead_data, correct_lead_data, generate_lead_dossier_dict
from leads.serializers import LeadSerializer
from leads.services import process_log_activity
from leads.timezone_utils import (
    check_calling_hours,
    format_datetime_in_timezone,
    get_default_timezone_for_state,
)
from masters.models import Outcome, PolicySettings, PublicHoliday, Region, State
from quotes.models import Quote

User = get_user_model()


@pytest.fixture
def regions_and_states(db):
    region_in, _ = Region.objects.get_or_create(
        code="IN",
        defaults={
            "name": "India",
            "currency": "INR",
            "currency_symbol": "₹",
            "default_timezone": "Asia/Kolkata",
            "phone_country_code": "+91",
            "locale": "en-IN",
            "tax_label": "GST",
            "tax_rate": 0.05,
            "incentive_label": "Subsidy",
            "calling_hours_policy": "warn",
        },
    )
    region_au, _ = Region.objects.get_or_create(
        code="AU",
        defaults={
            "name": "Australia",
            "currency": "AUD",
            "currency_symbol": "A$",
            "default_timezone": "Australia/Sydney",
            "phone_country_code": "+61",
            "locale": "en-AU",
            "tax_label": "GST",
            "tax_rate": 0.10,
            "incentive_label": "Government incentive (STCs and rebates)",
            "calling_hours_policy": "warn",
            "sunday_calling_allowed": False,
        },
    )

    state_gj, _ = State.objects.get_or_create(
        region=region_in,
        code="GJ",
        defaults={"name": "Gujarat", "default_timezone": "Asia/Kolkata"},
    )
    state_nsw, _ = State.objects.get_or_create(
        region=region_au,
        code="NSW",
        defaults={"name": "New South Wales", "default_timezone": "Australia/Sydney"},
    )
    state_wa, _ = State.objects.get_or_create(
        region=region_au,
        code="WA",
        defaults={"name": "Western Australia", "default_timezone": "Australia/Perth"},
    )

    call_outcome, _ = Outcome.objects.get_or_create(
        stage="call",
        name="Connected & Interested",
        defaults={
            "default_status": Lead.Status.INTERESTED,
            "default_next_action": "Send {channel} brochure and calculate {incentive_label}",
            "default_followup_days": 2,
        },
    )

    return {
        "region_in": region_in,
        "region_au": region_au,
        "state_gj": state_gj,
        "state_nsw": state_nsw,
        "state_wa": state_wa,
        "call_outcome": call_outcome,
    }


@pytest.fixture
def users(db, regions_and_states):
    reg_in = regions_and_states["region_in"]
    reg_au = regions_and_states["region_au"]

    admin = User.objects.create_superuser("test_admin", "admin@solar.crm", "admin123")

    manager = User.objects.create_user(
        username="mgr_global",
        password="password123",
        role=User.Role.MANAGER,
        default_region=reg_in,
    )
    manager.allowed_regions.set([reg_in, reg_au])

    sales_in = User.objects.create_user(
        username="sales_india",
        password="password123",
        role=User.Role.SALESPERSON,
        default_region=reg_in,
    )
    sales_in.allowed_regions.set([reg_in])

    sales_au = User.objects.create_user(
        username="sales_australia",
        password="password123",
        role=User.Role.SALESPERSON,
        default_region=reg_au,
    )
    sales_au.allowed_regions.set([reg_au])

    return {
        "admin": admin,
        "manager": manager,
        "sales_in": sales_in,
        "sales_au": sales_au,
    }


# =========================================================================
# 1. Phone Normalization & E.164 Tests
# =========================================================================
@pytest.mark.django_db
class TestPhoneNormalizationAndE164:
    def test_indian_phone_normalization(self, regions_and_states):
        e164_1, disp_1, err_1 = normalize_phone_number("9825012345", "IN")
        assert err_1 is None
        assert e164_1 == "+919825012345"

        e164_2, disp_2, err_2 = normalize_phone_number("+91 98250 12345", "IN")
        assert err_2 is None
        assert e164_2 == "+919825012345"

        e164_3, disp_3, err_3 = normalize_phone_number("09825012345", "IN")
        assert err_3 is None
        assert e164_3 == "+919825012345"

    def test_australian_phone_normalization(self, regions_and_states):
        # Australian Mobile 04xx xxx xxx
        e164_m, disp_m, err_m = normalize_phone_number("0412 345 678", "AU")
        assert err_m is None
        assert e164_m == "+61412345678"

        # Australian with country code
        e164_m2, disp_m2, err_m2 = normalize_phone_number("+61 412 345 678", "AU")
        assert err_m2 is None
        assert e164_m2 == "+61412345678"

        # Australian Landline NSW 02 xxxx xxxx
        e164_l, disp_l, err_l = normalize_phone_number("02 9876 5432", "AU")
        assert err_l is None
        assert e164_l == "+61298765432"

    def test_invalid_phone_returns_error(self, regions_and_states):
        _, _, err_in = normalize_phone_number("12345", "IN")
        assert err_in is not None

        _, _, err_au = normalize_phone_number("invalid_phone", "AU")
        assert err_au is not None


# =========================================================================
# 2. Postal Code & Address Validation Tests
# =========================================================================
@pytest.mark.django_db
class TestPostalCodeValidation:
    def test_postcode_validation_in_serializer(self, regions_and_states):
        reg_in = regions_and_states["region_in"]
        reg_au = regions_and_states["region_au"]

        # India valid 6 digits
        ser_in_ok = LeadSerializer(
            data={"name": "A", "phone": "9825012345", "region": "IN", "city": "Ahmedabad", "pincode": "380015"}
        )
        assert ser_in_ok.is_valid(), ser_in_ok.errors
        assert ser_in_ok.validated_data["pincode"] == "380015"

        # India invalid (4 digits)
        ser_in_bad = LeadSerializer(
            data={"name": "A", "phone": "9825012345", "region": "IN", "city": "Ahmedabad", "pincode": "3000"}
        )
        assert not ser_in_bad.is_valid()
        assert "pincode" in ser_in_bad.errors

        # Australia valid 4 digits
        ser_au_ok = LeadSerializer(
            data={"name": "B", "phone": "0412345678", "region": "AU", "city": "Melbourne", "postcode": "3000"}
        )
        assert ser_au_ok.is_valid(), ser_au_ok.errors
        assert ser_au_ok.validated_data["postcode"] == "3000"

        # Australia invalid (6 digits)
        ser_au_bad = LeadSerializer(
            data={"name": "B", "phone": "0412345678", "region": "AU", "city": "Melbourne", "postcode": "380015"}
        )
        assert not ser_au_bad.is_valid()
        assert "postcode" in ser_au_bad.errors


# =========================================================================
# 3. Timezone Derivation & Calling Hours Evaluation Tests
# =========================================================================
@pytest.mark.django_db
class TestTimezonesAndCallingHours:
    def test_timezone_derivation(self, regions_and_states):
        assert get_default_timezone_for_state("IN", "GJ") == "Asia/Kolkata"
        assert get_default_timezone_for_state("AU", "NSW") == "Australia/Sydney"
        assert get_default_timezone_for_state("AU", "WA") == "Australia/Perth"

    def test_calling_hours_weekday(self, regions_and_states):
        reg_au = regions_and_states["region_au"]
        lead = Lead.objects.create(
            region=reg_au,
            name="Test AU",
            phone="0412345678",
            city="Sydney",
            state="NSW",
            timezone="Australia/Sydney",
            status=Lead.Status.NEW,
        )

        # Tuesday at 11:00 AM Sydney time -> Permitted
        sydney_tz = zoneinfo.ZoneInfo("Australia/Sydney")
        dt_ok = datetime(2026, 6, 2, 11, 0, tzinfo=sydney_tz)  # Tuesday
        is_ok, msg = check_calling_hours(lead, target_datetime=dt_ok)
        assert is_ok is True

        # Tuesday at 21:30 (9:30 PM) -> Blocked/Outside
        dt_late = datetime(2026, 6, 2, 21, 30, tzinfo=sydney_tz)
        is_ok2, msg2 = check_calling_hours(lead, target_datetime=dt_late)
        assert is_ok2 is False
        assert "outside" in msg2.lower() or "calling hours" in msg2.lower()

    def test_calling_hours_australia_saturday_and_sunday(self, regions_and_states):
        reg_au = regions_and_states["region_au"]
        sydney_tz = zoneinfo.ZoneInfo("Australia/Sydney")
        lead = Lead.objects.create(
            region=reg_au,
            name="Test AU",
            phone="0412345678",
            city="Sydney",
            state="NSW",
            timezone="Australia/Sydney",
            status=Lead.Status.NEW,
        )

        # Saturday at 18:30 (AU closes at 17:00 on Saturdays)
        dt_sat_late = datetime(2026, 6, 6, 18, 30, tzinfo=sydney_tz)  # Saturday
        is_ok_sat, _ = check_calling_hours(lead, target_datetime=dt_sat_late)
        assert is_ok_sat is False

        # Sunday -> Strictly closed in AU
        dt_sun = datetime(2026, 6, 7, 12, 0, tzinfo=sydney_tz)  # Sunday
        is_ok_sun, msg_sun = check_calling_hours(lead, target_datetime=dt_sun)
        assert is_ok_sun is False
        assert "sunday" in msg_sun.lower()

    def test_public_holiday_blocks_calling(self, regions_and_states):
        reg_in = regions_and_states["region_in"]
        kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        holiday_date = date(2026, 8, 15)

        PublicHoliday.objects.create(
            region=reg_in,
            name="Independence Day",
            date=holiday_date,
        )

        lead = Lead.objects.create(
            region=reg_in,
            name="Test IN",
            phone="9825012345",
            city="Ahmedabad",
            timezone="Asia/Kolkata",
            status=Lead.Status.NEW,
        )

        dt_holiday = datetime(2026, 8, 15, 12, 0, tzinfo=kolkata_tz)
        is_ok, msg = check_calling_hours(lead, target_datetime=dt_holiday)
        assert is_ok is False
        assert "Independence Day" in msg


# =========================================================================
# 4. Calling Hours Override & AuditLog Immutability Tests
# =========================================================================
@pytest.mark.django_db
class TestAuditLogAndCallingHoursOverride:
    def test_calling_hours_override_logs_audit(self, regions_and_states, users):
        reg_au = regions_and_states["region_au"]
        sales_au = users["sales_au"]
        outcome = regions_and_states["call_outcome"]

        lead = Lead.objects.create(
            region=reg_au,
            name="Matilda Jones",
            phone="0411222333",
            city="Sydney",
            state="NSW",
            assigned_to=sales_au,
            status=Lead.Status.NEW,
            next_action="Call customer",
            next_followup_at=timezone.now(),
        )

        # Mock check_calling_hours to return False (outside hours)
        with patch("leads.timezone_utils.check_calling_hours", return_value=(False, "Restricted evening hours")):
            # 1. Attempting call without override reason must fail
            with pytest.raises(ValidationError) as exc_info:
                process_log_activity(
                    lead=lead,
                    user=sales_au,
                    data={
                        "type": "call",
                        "outcome": outcome,
                        "notes": "Attempted call outside hours",
                        "status": Lead.Status.ATTEMPTING_CONTACT,
                        "next_action": "Try next day",
                        "next_followup_at": timezone.now() + timedelta(days=1),
                    },
                )
            assert "override reason is required" in str(exc_info.value).lower()

            # 2. Providing valid override reason succeeds and creates AuditLog entry
            activity, updated_lead = process_log_activity(
                lead=lead,
                user=sales_au,
                data={
                    "type": "call",
                    "outcome": outcome,
                    "notes": "Spoke to Matilda at agreed time",
                    "calling_hours_override_reason": "Customer requested evening call after work",
                    "status": Lead.Status.INTERESTED,
                    "next_action": "Send SMS quote",
                    "next_followup_at": timezone.now() + timedelta(days=2),
                },
                ip_address="127.0.0.1",
            )

            assert updated_lead.status == Lead.Status.INTERESTED
            assert updated_lead.attempt_count == 0  # reset on answered/interested

            # Verify immutable AuditLog created
            audit_entry = AuditLog.objects.filter(
                lead=lead, action='calling_hours_override'
            ).first()
            assert audit_entry is not None
            assert audit_entry.user == sales_au
            assert "Customer requested evening call" in audit_entry.reason

    def test_audit_log_is_immutable(self, regions_and_states, users):
        lead = Lead.objects.create(
            region=regions_and_states["region_in"],
            name="Test Lead",
            phone="9825000000",
            city="Ahmedabad",
            status=Lead.Status.NEW,
        )

        entry = AuditLog.objects.create(
            user=users["admin"],
            action='calling_hours_override',
            lead=lead,
            reason="Test immutable log",
            details={"notes": "test"},
        )

        # Modifying entry must raise ValueError
        entry.reason = "Altered reason"
        with pytest.raises(ValueError, match="AuditLog entries are tamper-evident and immutable"):
            entry.save()

        # Deleting entry must raise ValueError
        with pytest.raises(ValueError, match="AuditLog entries are tamper-evident and immutable"):
            entry.delete()


# =========================================================================
# 5. Region-Based Access Control (RBAC) API Tests
# =========================================================================
@pytest.mark.django_db
class TestRegionAccessControl:
    def test_salesperson_region_isolation(self, regions_and_states, users):
        reg_in = regions_and_states["region_in"]
        reg_au = regions_and_states["region_au"]
        sales_in = users["sales_in"]
        sales_au = users["sales_au"]
        manager = users["manager"]

        lead_in = Lead.objects.create(
            region=reg_in,
            name="Rajesh Patel",
            phone="9825011111",
            city="Ahmedabad",
            assigned_to=sales_in,
            status=Lead.Status.NEW,
        )
        lead_au = Lead.objects.create(
            region=reg_au,
            name="Jack Thompson",
            phone="0412999888",
            city="Sydney",
            assigned_to=sales_au,
            status=Lead.Status.NEW,
        )

        client = APIClient()

        # Sales India can only see lead_in
        client.force_authenticate(user=sales_in)
        res_in = client.get("/api/leads/")
        assert res_in.status_code == status.HTTP_200_OK
        items_in = res_in.data.get("results") if isinstance(res_in.data, dict) else res_in.data
        ids_in = [item["id"] for item in items_in]
        assert lead_in.id in ids_in
        assert lead_au.id not in ids_in

        # Sales Australia can only see lead_au
        client.force_authenticate(user=sales_au)
        res_au = client.get("/api/leads/")
        assert res_au.status_code == status.HTTP_200_OK
        items_au = res_au.data.get("results") if isinstance(res_au.data, dict) else res_au.data
        ids_au = [item["id"] for item in items_au]
        assert lead_au.id in ids_au
        assert lead_in.id not in ids_au

        # Manager with both allowed regions can see both leads
        client.force_authenticate(user=manager)
        res_mgr = client.get("/api/leads/")
        assert res_mgr.status_code == status.HTTP_200_OK
        items_mgr = res_mgr.data.get("results") if isinstance(res_mgr.data, dict) else res_mgr.data
        ids_mgr = [item["id"] for item in items_mgr]
        assert lead_in.id in ids_mgr
        assert lead_au.id in ids_mgr

        # Filtering by ?region=AU shows only AU
        res_filter = client.get("/api/leads/?region=AU")
        assert res_filter.status_code == status.HTTP_200_OK
        items_filter = res_filter.data.get("results") if isinstance(res_filter.data, dict) else res_filter.data
        ids_filter = [item["id"] for item in items_filter]
        assert lead_au.id in ids_filter
        assert lead_in.id not in ids_filter


# =========================================================================
# 6. Cross-Region Duplicate Detection via E.164 Tests
# =========================================================================
@pytest.mark.django_db
class TestCrossRegionDuplicateDetection:
    def test_duplicate_phone_e164_detected(self, regions_and_states, users):
        reg_in = regions_and_states["region_in"]
        Lead.objects.create(
            region=reg_in,
            name="Existing Customer",
            phone="+919825099999",
            phone_e164="+919825099999",
            city="Ahmedabad",
            status=Lead.Status.NEW,
        )

        client = APIClient()
        client.force_authenticate(user=users["admin"])

        # Try creating duplicate with spacing / country code
        payload = {
            "name": "Duplicate Entry",
            "phone": "+91 98250 99999",
            "region": "IN",
            "city": "Ahmedabad",
        }
        res = client.post("/api/leads/", payload, format="json")
        assert res.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]
        assert "True" in str(res.data.get("duplicate")) or bool(res.data.get("duplicate")) is True
        assert "already exists" in str(res.data)

        # Force create works
        res_force = client.post("/api/leads/?force=true", payload, format="json")
        assert res_force.status_code == status.HTTP_201_CREATED


# =========================================================================
# 7. Quote Snapshot & Regional Financials Tests
# =========================================================================
@pytest.mark.django_db
class TestQuoteRegionalSnapshot:
    def test_australian_quote_snapshot_and_battery(self, regions_and_states, users):
        reg_au = regions_and_states["region_au"]
        lead_au = Lead.objects.create(
            region=reg_au,
            name="Oliver Brown",
            phone="0412111222",
            city="Melbourne",
            state="VIC",
            status=Lead.Status.DESIGN_PENDING,
        )

        client = APIClient()
        client.force_authenticate(user=users["admin"])

        payload = {
            "lead_id": lead_au.id,
            "system_size_kw": 6.6,
            "battery_kwh": 9.6,
            "brand": "Trina 440W + Sungrow 5kW Hybrid",
            "price": 8900.0,
            "subsidy_amount": 2900.0,
            "notes": "CEC approved design",
        }
        res = client.post("/api/quotes/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED

        quote = Quote.objects.get(id=res.data["id"])
        assert quote.currency == "AUD"
        assert quote.currency_symbol == "A$"
        assert quote.tax_included is True
        assert float(quote.tax_rate) == 0.10
        assert float(quote.battery_kwh) == 9.6
        assert "incentive" in quote.incentive_label.lower()

        # Modify region tax rate: existing quote snapshot must remain 0.10
        reg_au.tax_rate = 0.125
        reg_au.save()

        quote.refresh_from_db()
        assert float(quote.tax_rate) == 0.10


# =========================================================================
# 8. Privacy DSAR Export, Anonymization & Rectification Tests
# =========================================================================
@pytest.mark.django_db
class TestPrivacyComplianceServices:
    def test_privacy_dsar_export_json_and_pdf(self, regions_and_states, users):
        lead = Lead.objects.create(
            region=regions_and_states["region_au"],
            name="Chloe Davies",
            phone="0412333444",
            email="chloe.davies@example.com.au",
            address="15 River St",
            suburb="South Yarra",
            postcode="3141",
            city="Melbourne",
            status=Lead.Status.QUOTE_SENT,
        )

        client = APIClient()
        client.force_authenticate(user=users["admin"])

        # JSON Export
        res_json = client.get(f"/api/leads/{lead.id}/privacy-export/?format=json")
        assert res_json.status_code == status.HTTP_200_OK
        data = res_json.data
        assert data["lead_profile"]["name"] == "Chloe Davies"
        assert data["lead_profile"]["phone"] == "+61412333444"
        assert data["lead_profile"]["region"] == "AU"
        assert "export_metadata" in data

        # PDF Export
        res_pdf = client.get(f"/api/leads/{lead.id}/privacy-export/?format=pdf")
        assert res_pdf.status_code == status.HTTP_200_OK
        assert res_pdf["Content-Type"] == "application/pdf"
        assert len(res_pdf.content) > 1000

        # Verify bulk export was logged to AuditLog
        assert AuditLog.objects.filter(
            lead=lead, action='privacy_export'
        ).exists()

    def test_lead_anonymization(self, regions_and_states, users):
        lead = Lead.objects.create(
            region=regions_and_states["region_in"],
            name="Suresh Joshi",
            phone="9825044444",
            email="suresh.joshi@example.com",
            address="404 Swastik Chambers",
            city="Ahmedabad",
            status=Lead.Status.INTERESTED,
        )

        anonymized = anonymize_lead_data(
            lead=lead,
            reason="Customer invoked DPDP Right to Erasure",
            user=users["admin"],
        )

        assert anonymized.name == f"Anonymized Lead #{lead.id}"
        assert anonymized.phone.startswith("+91000000")
        assert anonymized.email == ""
        assert anonymized.address.startswith("Redacted")
        assert anonymized.do_not_contact is True
        assert anonymized.consent_status == "withdrawn"

        # AuditLog entry created
        audit = AuditLog.objects.filter(
            lead=lead, action='anonymize_lead'
        ).first()
        assert audit is not None
        assert "DPDP Right to Erasure" in audit.reason

    def test_lead_data_rectification(self, regions_and_states, users):
        lead = Lead.objects.create(
            region=regions_and_states["region_in"],
            name="Meera Desai",
            phone="9825055555",
            email="wrong.email@example.com",
            city="Ahmedabad",
            status=Lead.Status.NEW,
        )

        corrected = correct_lead_data(
            lead=lead,
            updates={"email": "meera.desai@example.com", "city": "Surat"},
            reason="Customer requested correction of contact details",
            user=users["admin"],
        )

        assert corrected.email == "meera.desai@example.com"
        assert corrected.city == "Surat"

        audit = AuditLog.objects.filter(
            lead=lead, action='correct_lead_data'
        ).first()
        assert audit is not None
        assert "wrong.email@example.com" in audit.details["changes"]["email"]["old"]
        assert "meera.desai@example.com" in audit.details["changes"]["email"]["new"]


# =========================================================================
# 9. Dashboard Segregated Currency Totals Tests
# =========================================================================
@pytest.mark.django_db
class TestDashboardCurrencySegregation:
    def test_dashboard_separates_won_currencies(self, regions_and_states, users):
        reg_in = regions_and_states["region_in"]
        reg_au = regions_and_states["region_au"]

        lead_in = Lead.objects.create(
            region=reg_in,
            name="Won India Lead",
            phone="9825077777",
            city="Ahmedabad",
            status=Lead.Status.WON,
            won_at=timezone.now(),
        )
        Quote.objects.create(
            lead=lead_in,
            region=reg_in,
            currency="INR",
            currency_symbol="₹",
            system_size_kw=5.0,
            brand="Waaree",
            price=250000,
            status=Quote.Status.ACCEPTED,
        )

        lead_au = Lead.objects.create(
            region=reg_au,
            name="Won AU Lead",
            phone="0412888777",
            city="Sydney",
            status=Lead.Status.WON,
            won_at=timezone.now(),
        )
        Quote.objects.create(
            lead=lead_au,
            region=reg_au,
            currency="AUD",
            currency_symbol="A$",
            system_size_kw=6.6,
            brand="Sungrow",
            price=9500,
            status=Quote.Status.ACCEPTED,
        )

        client = APIClient()
        client.force_authenticate(user=users["manager"])

        res = client.get("/api/dashboard/")
        assert res.status_code == status.HTTP_200_OK

        won_currencies = res.data.get("won_value_by_currency", {})
        # Currencies must be isolated in dict, never merged
        assert won_currencies.get("INR") == 250000.0
        assert won_currencies.get("AUD") == 9500.0
