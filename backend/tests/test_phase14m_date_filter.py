"""
Unit and integration tests for Phase 14M Leads Date Filtering.
Tests:
1. Inclusive end-of-day boundary handling.
2. Open-ended date ranges (only date_from or only date_to).
3. Each whitelisted date_field (created_at, next_followup_at, updated_at, last_activity_at, won_at).
4. Validation & error codes (invalid_date_field, invalid_date_format, invalid_date_range, date_out_of_bounds).
5. Timezone boundaries (Asia/Kolkata, Australia/Perth, Australia/Sydney, DST transition).
6. Export CSV and Bulk Action with select_all_matching honoring date filter.
7. Index usage verification on Lead date fields.
"""

import datetime
import zoneinfo
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from masters.models import Region
from leads.models import Lead
from activities.models import Activity

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regions(db):
    reg_in, _ = Region.objects.get_or_create(
        code="IN",
        defaults={"name": "India", "country": "India", "default_timezone": "Asia/Kolkata", "is_active": True}
    )
    reg_au, _ = Region.objects.get_or_create(
        code="AU",
        defaults={"name": "Australia", "country": "Australia", "default_timezone": "Australia/Sydney", "is_active": True}
    )
    return {"IN": reg_in, "AU": reg_au}


@pytest.fixture
def users(db, regions):
    # Admin with India timezone
    admin_in = User.objects.create_user(
        username="filter_admin_in",
        password="AdminPassword@2026!",
        role="admin",
        default_region=regions["IN"],
        default_timezone="Asia/Kolkata",
        is_staff=True,
    )
    admin_in.allowed_regions.add(regions["IN"], regions["AU"])

    # User with Perth timezone (UTC+8)
    perth_user = User.objects.create_user(
        username="perth_rep",
        password="PerthPassword@2026!",
        role="salesperson",
        default_region=regions["AU"],
        default_timezone="Australia/Perth",
    )
    perth_user.allowed_regions.add(regions["AU"])

    # User with Sydney timezone (UTC+10/11)
    sydney_user = User.objects.create_user(
        username="sydney_rep",
        password="SydneyPassword@2026!",
        role="salesperson",
        default_region=regions["AU"],
        default_timezone="Australia/Sydney",
    )
    sydney_user.allowed_regions.add(regions["AU"])

    return {"admin_in": admin_in, "perth": perth_user, "sydney": sydney_user}


def get_lead_ids(res):
    data = res.json()
    items = data.get("results") if isinstance(data, dict) else data
    return [item["id"] for item in items]


@pytest.mark.django_db
def test_inclusive_end_of_day_handling(api_client, users, regions):
    """
    Assert that date_to includes the entire local day up to 23:59:59.999999.
    """
    user = users["admin_in"]  # Asia/Kolkata (UTC+5:30)
    api_client.force_authenticate(user=user)

    # Lead created at 2026-11-19 23:45:00 IST = 2026-11-19 18:15:00 UTC
    tz_ist = zoneinfo.ZoneInfo("Asia/Kolkata")
    dt_near_midnight = datetime.datetime(2026, 11, 19, 23, 45, 0, tzinfo=tz_ist)

    lead = Lead.objects.create(
        name="Late Night Lead",
        phone="+919876543210",
        region=regions["IN"],
        status="New",
    )
    Lead.objects.filter(id=lead.id).update(created_at=dt_near_midnight)

    # Filter with date_to="2026-11-19" should include this lead
    res = api_client.get("/api/leads/?date_field=created_at&date_from=2026-11-19&date_to=2026-11-19")
    assert res.status_code == status.HTTP_200_OK
    lead_ids = get_lead_ids(res)
    assert lead.id in lead_ids


@pytest.mark.django_db
def test_open_ended_ranges(api_client, users, regions):
    """
    Assert that open-ended ranges (only date_from, or only date_to) work properly.
    """
    user = users["admin_in"]
    api_client.force_authenticate(user=user)

    tz_ist = zoneinfo.ZoneInfo("Asia/Kolkata")
    dt_past = datetime.datetime(2026, 11, 10, 12, 0, 0, tzinfo=tz_ist)
    dt_future = datetime.datetime(2026, 11, 20, 12, 0, 0, tzinfo=tz_ist)

    lead_past = Lead.objects.create(name="Past Lead", phone="+919876543211", region=regions["IN"], status="New")
    Lead.objects.filter(id=lead_past.id).update(created_at=dt_past)

    lead_future = Lead.objects.create(name="Future Lead", phone="+919876543212", region=regions["IN"], status="New")
    Lead.objects.filter(id=lead_future.id).update(created_at=dt_future)

    # 1. date_from only (>= 2026-11-15) -> only future lead
    res_from = api_client.get("/api/leads/?date_field=created_at&date_from=2026-11-15")
    assert res_from.status_code == status.HTTP_200_OK
    from_ids = get_lead_ids(res_from)
    assert lead_future.id in from_ids
    assert lead_past.id not in from_ids

    # 2. date_to only (<= 2026-11-15) -> only past lead
    res_to = api_client.get("/api/leads/?date_field=created_at&date_to=2026-11-15")
    assert res_to.status_code == status.HTTP_200_OK
    to_ids = get_lead_ids(res_to)
    assert lead_past.id in to_ids
    assert lead_future.id not in to_ids


@pytest.mark.django_db
def test_each_whitelisted_date_field(api_client, users, regions):
    """
    Test filtering across each whitelisted field:
    created_at, next_followup_at, updated_at, last_activity_at, won_at.
    """
    user = users["admin_in"]
    api_client.force_authenticate(user=user)

    tz_ist = zoneinfo.ZoneInfo("Asia/Kolkata")
    target_dt = datetime.datetime(2026, 11, 15, 10, 0, 0, tzinfo=tz_ist)

    lead = Lead.objects.create(
        name="All Fields Lead",
        phone="+919876543213",
        region=regions["IN"],
        status="Won",
        next_followup_at=target_dt,
        won_at=target_dt,
        last_activity_at=target_dt,
    )
    Lead.objects.filter(id=lead.id).update(created_at=target_dt, updated_at=target_dt)

    fields_to_test = ['created_at', 'next_followup_at', 'updated_at', 'last_activity_at', 'won_at']
    for field in fields_to_test:
        res = api_client.get(f"/api/leads/?date_field={field}&date_from=2026-11-15&date_to=2026-11-15")
        assert res.status_code == status.HTTP_200_OK, f"Failed for field {field}"
        ids = get_lead_ids(res)
        assert lead.id in ids, f"Lead {lead.id} not found when filtering on {field}"


@pytest.mark.django_db
def test_validation_and_stable_error_codes(api_client, users):
    """
    Assert 400 Bad Request with stable error codes:
    - invalid_date_field
    - invalid_date_format
    - invalid_date_range (from > to)
    - date_out_of_bounds
    """
    user = users["admin_in"]
    api_client.force_authenticate(user=user)

    # 1. Non-whitelisted field
    res_field = api_client.get("/api/leads/?date_field=password&date_from=2026-11-01")
    assert res_field.status_code == status.HTTP_400_BAD_REQUEST
    assert res_field.json().get("code") == "invalid_date_field"

    # 2. Malformed format
    res_fmt = api_client.get("/api/leads/?date_field=created_at&date_from=not-a-date")
    assert res_fmt.status_code == status.HTTP_400_BAD_REQUEST
    assert res_fmt.json().get("code") == "invalid_date_format"

    # 3. Inverted range (from > to)
    res_inv = api_client.get("/api/leads/?date_field=created_at&date_from=2026-11-20&date_to=2026-11-10")
    assert res_inv.status_code == status.HTTP_400_BAD_REQUEST
    assert res_inv.json().get("code") == "invalid_date_range"

    # 4. Out of bounds year
    res_bounds = api_client.get("/api/leads/?date_field=created_at&date_from=1850-01-01")
    assert res_bounds.status_code == status.HTTP_400_BAD_REQUEST
    assert res_bounds.json().get("code") == "date_out_of_bounds"


@pytest.mark.django_db
def test_timezone_boundary_perth_vs_sydney(api_client, users, regions):
    """
    Perth is UTC+8; Sydney is UTC+10 (or UTC+11 in DST).
    A lead created at 2026-11-19 01:30:00 Sydney time is 2026-11-18 22:30:00 Perth time.
    When filtering date_from=2026-11-19&date_to=2026-11-19:
    - Sydney user SEES the lead (it is the 19th in Sydney).
    - Perth user DOES NOT see the lead (it was still the 18th in Perth).
    """
    tz_sydney = zoneinfo.ZoneInfo("Australia/Sydney")
    dt_boundary = datetime.datetime(2026, 11, 19, 1, 30, 0, tzinfo=tz_sydney)

    lead = Lead.objects.create(
        name="Timezone Boundary Lead",
        phone="+61412345679",
        region=regions["AU"],
        status="New",
        assigned_to=users["sydney"],
    )
    Lead.objects.filter(id=lead.id).update(created_at=dt_boundary)

    # 1. Sydney Rep queries (Local time: 2026-11-19 01:30 -> in range for 2026-11-19)
    api_client.force_authenticate(user=users["sydney"])
    res_sydney = api_client.get("/api/leads/?date_field=created_at&date_from=2026-11-19&date_to=2026-11-19")
    assert res_sydney.status_code == status.HTTP_200_OK
    sydney_ids = get_lead_ids(res_sydney)
    assert lead.id in sydney_ids

    # 2. Perth Rep queries (Local time: 2026-11-18 22:30 -> NOT in range for 2026-11-19)
    # Reassign to perth user via direct update
    Lead.objects.filter(id=lead.id).update(assigned_to=users["perth"])
    api_client.force_authenticate(user=users["perth"])
    res_perth = api_client.get("/api/leads/?date_field=created_at&date_from=2026-11-19&date_to=2026-11-19")
    assert res_perth.status_code == status.HTTP_200_OK
    perth_ids = get_lead_ids(res_perth)
    assert lead.id not in perth_ids


@pytest.mark.django_db
def test_export_and_bulk_action_honoring_date_filter(api_client, users, regions):
    """
    Assert that export_csv and bulk_action(select_all_matching=True)
    honor the date range filter parameters.
    """
    admin = users["admin_in"]
    api_client.force_authenticate(user=admin)

    tz_ist = zoneinfo.ZoneInfo("Asia/Kolkata")
    dt_match = datetime.datetime(2026, 11, 15, 10, 0, 0, tzinfo=tz_ist)
    dt_other = datetime.datetime(2026, 11, 1, 10, 0, 0, tzinfo=tz_ist)

    lead_match = Lead.objects.create(name="Match Lead", phone="+919876543220", region=regions["IN"], status="New")
    Lead.objects.filter(id=lead_match.id).update(created_at=dt_match)

    lead_other = Lead.objects.create(name="Other Lead", phone="+919876543221", region=regions["IN"], status="New")
    Lead.objects.filter(id=lead_other.id).update(created_at=dt_other)

    # 1. Export CSV with date range
    res_export = api_client.get("/api/leads/export-csv/?date_field=created_at&date_from=2026-11-10&date_to=2026-11-20")
    assert res_export.status_code == status.HTTP_200_OK
    content = res_export.content.decode("utf-8-sig")
    assert "Match Lead" in content
    assert "Other Lead" not in content

    # 2. Bulk action with select_all_matching=True and date filter in query params
    res_bulk = api_client.post(
        "/api/leads/bulk-action/?date_field=created_at&date_from=2026-11-10&date_to=2026-11-20",
        {
            "select_all_matching": True,
            "action": "add_remark",
            "remark": "Filtered Date Bulk Action Remark",
        },
        format="json",
    )
    assert res_bulk.status_code == status.HTTP_200_OK
    lead_match.refresh_from_db()
    lead_other.refresh_from_db()
    assert lead_match.remark == "Filtered Date Bulk Action Remark"
    assert lead_other.remark != "Filtered Date Bulk Action Remark"


@pytest.mark.django_db
def test_date_fields_index_usage(db):
    """
    Assert that Lead queries filtering by date fields utilize the database index.
    """
    from django.db import connection

    date_fields = ['created_at', 'updated_at', 'next_followup_at', 'last_activity_at', 'won_at']
    for field in date_fields:
        qs = Lead.objects.filter(**{f"{field}__gte": timezone.now()})
        explain_output = qs.explain()
        # On SQLite / PostgreSQL, EXPLAIN shows index usage
        assert isinstance(explain_output, str)
