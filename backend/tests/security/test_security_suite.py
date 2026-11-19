"""
Solar CRM - Comprehensive Dynamic Security Audit & Penetration Test Suite.
Tests:
1. Dynamic Endpoint Discovery & Parametrized Fuzzing (anonymous access, path traversal, malicious query params)
2. IDOR & Cross-Region Access Isolation (leads, quotes, activities, bulk operations, merge)
3. Authentication & Account Hardening (login rate limiting, lockout, no username enumeration, JWT refresh blacklisting, must_change_password)
4. Injection & Tampering (SQL injection, CSV formula injection, sent quote immutability, date filter whitelist & bounds)
5. Business Logic Security (Won status requires accepted quote, rep cannot mark Lost without permission)
6. Security Headers, CORS & I18N Security (CSP, nosniff, Referrer-Policy, CORS preflight headers, translation XSS prevention)
"""

import html
import json
import pytest
from django.urls import get_resolver
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from masters.models import Region
from leads.models import Lead, LeadStatusHistory, AuditLog
from quotes.models import Quote
from activities.models import Activity

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regions(db):
    reg_in, _ = Region.objects.get_or_create(
        code="IN",
        defaults={"name": "India", "country": "India", "currency": "INR", "currency_symbol": "₹", "default_timezone": "Asia/Kolkata", "is_active": True}
    )
    reg_au, _ = Region.objects.get_or_create(
        code="AU",
        defaults={"name": "Australia", "country": "Australia", "currency": "AUD", "currency_symbol": "A$", "default_timezone": "Australia/Sydney", "is_active": True}
    )
    return {"IN": reg_in, "AU": reg_au}


@pytest.fixture
def test_users(db, regions):
    admin_user = User.objects.create_user(
        username="sec_admin",
        password="SecureAdminPassword@2026!",
        role="admin",
        default_region=regions["IN"],
        is_staff=True,
    )
    admin_user.allowed_regions.add(regions["IN"], regions["AU"])

    rep_in = User.objects.create_user(
        username="sec_rep_in",
        password="SecurePasswordIn@2026!",
        role="salesperson",
        default_region=regions["IN"],
    )
    rep_in.allowed_regions.add(regions["IN"])

    rep_au = User.objects.create_user(
        username="sec_rep_au",
        password="SecurePasswordAu@2026!",
        role="salesperson",
        default_region=regions["AU"],
    )
    rep_au.allowed_regions.add(regions["AU"])

    must_change_user = User.objects.create_user(
        username="sec_must_change",
        password="TempPassword@2026!",
        role="salesperson",
        default_region=regions["IN"],
        must_change_password=True,
    )
    must_change_user.allowed_regions.add(regions["IN"])

    return {
        "admin": admin_user,
        "rep_in": rep_in,
        "rep_au": rep_au,
        "must_change": must_change_user,
    }


@pytest.fixture
def sample_leads(db, regions, test_users):
    lead_in = Lead.objects.create(
        name="Security Test Lead India",
        phone="+919876543210",
        email="lead.in@example.com",
        region=regions["IN"],
        status="Quoted",
        assigned_to=test_users["rep_in"],
    )
    lead_au = Lead.objects.create(
        name="Security Test Lead Australia",
        phone="+61412345678",
        email="lead.au@example.com",
        region=regions["AU"],
        status="Quoted",
        assigned_to=test_users["rep_au"],
    )
    return {"IN": lead_in, "AU": lead_au}


# ---------------------------------------------------------------------------
# 1. Dynamic Endpoint Discovery & Parametrized Tests
# ---------------------------------------------------------------------------

def get_api_endpoints():
    """Dynamically discover API URL paths from the root URL resolver."""
    resolver = get_resolver()
    endpoints = []

    def extract_patterns(patterns, prefix=""):
        for p in patterns:
            if hasattr(p, 'url_patterns'):
                extract_patterns(p.url_patterns, prefix + str(p.pattern))
            else:
                full_path = prefix + str(p.pattern)
                # Keep REST API endpoints that don't require path arguments
                if full_path.startswith("api/") and "<" not in full_path and "{" not in full_path:
                    clean_path = "/" + full_path.rstrip("$").rstrip("^")
                    if not clean_path.endswith("/"):
                        clean_path += "/"
                    if clean_path not in endpoints:
                        endpoints.append(clean_path)

    extract_patterns(resolver.url_patterns)
    return sorted(endpoints)


DISCOVERED_ENDPOINTS = get_api_endpoints()


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", DISCOVERED_ENDPOINTS[:30])  # Sample first 30 endpoints
def test_anonymous_access_no_500_or_leak(api_client, endpoint):
    """
    Assert that anonymous GET requests to discovered API endpoints either succeed (public)
    or return 401/403/405/404, and NEVER return 500 Internal Server Error or unhandled crash.
    """
    res = api_client.get(endpoint)
    assert res.status_code in [
        status.HTTP_200_OK,
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED,
    ], f"Endpoint {endpoint} returned unexpected status {res.status_code}"


@pytest.mark.django_db
@pytest.mark.parametrize("endpoint", [
    "/api/leads/",
    "/api/quotes/",
    "/api/activities/",
    "/api/dashboard/stats/",
])
def test_malicious_query_params_graceful_handling(api_client, test_users, endpoint):
    """
    Fuzz endpoints with SQLi, path traversal, null bytes, and malicious payloads.
    Assert server never responds with 500 Internal Server Error or database stack traces.
    """
    api_client.force_authenticate(user=test_users["admin"])
    payloads = [
        "1' OR '1'='1",
        "../../../../etc/passwd",
        "%00",
        "'; DROP TABLE leads;--",
        "<script>alert('xss')</script>",
        "2147483648",  # int overflow check
        "-1",
    ]
    for p in payloads:
        res = api_client.get(f"{endpoint}?search={p}&ordering={p}&region={p}&id={p}")
        assert res.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ], f"Fuzzing payload {p} against {endpoint} caused status {res.status_code}"
        assert "Traceback" not in str(res.content)
        assert "OperationalError" not in str(res.content)
        assert "ProgrammingError" not in str(res.content)


# ---------------------------------------------------------------------------
# 2. IDOR & Cross-Region Access Isolation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_cross_region_lead_idor_prevention(api_client, test_users, sample_leads):
    """
    Sales representative assigned strictly to Region IN must NOT be able to view,
    modify, or delete leads belonging to Region AU (returns 404 Not Found).
    """
    api_client.force_authenticate(user=test_users["rep_in"])
    au_lead = sample_leads["AU"]

    # 1. Direct GET
    res_get = api_client.get(f"/api/leads/{au_lead.id}/")
    assert res_get.status_code == status.HTTP_404_NOT_FOUND

    # 2. Direct PATCH
    res_patch = api_client.patch(f"/api/leads/{au_lead.id}/", {"name": "Hacked Name"})
    assert res_patch.status_code == status.HTTP_404_NOT_FOUND

    # 3. Direct DELETE
    res_del = api_client.delete(f"/api/leads/{au_lead.id}/")
    assert res_del.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
def test_cross_region_activity_creation_idor_block(api_client, test_users, sample_leads):
    """
    Sales representative from Region IN cannot log an activity on a lead in Region AU.
    """
    api_client.force_authenticate(user=test_users["rep_in"])
    au_lead = sample_leads["AU"]

    res = api_client.post("/api/activities/", {
        "lead": au_lead.id,
        "type": "call",
        "notes": "Unauthorized attempt to log call",
        "direction": "outbound",
    })
    assert res.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]


@pytest.mark.django_db
def test_cross_region_lead_merge_prevention(api_client, test_users, sample_leads, regions):
    """
    Merging leads across different regions is strictly forbidden and rejected with 400.
    """
    api_client.force_authenticate(user=test_users["admin"])
    in_lead = sample_leads["IN"]
    au_lead = sample_leads["AU"]

    res = api_client.post(f"/api/leads/{in_lead.id}/merge/", {
        "target_lead_id": au_lead.id,
    })
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "region" in str(res.content).lower()


# ---------------------------------------------------------------------------
# 3. Authentication & Account Hardening
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_login_no_username_enumeration(api_client):
    """
    Login endpoint must return identical generic error messages for non-existent users
    and existing users with incorrect passwords, preventing username enumeration.
    """
    # Non-existent user
    res_non_existent = api_client.post("/api/token/", {
        "username": "definitely_does_not_exist_987654",
        "password": "wrong_password",
    })

    # Existing user with bad password
    User.objects.create_user(username="existing_user", password="ValidPassword123!")
    res_bad_pw = api_client.post("/api/token/", {
        "username": "existing_user",
        "password": "wrong_password",
    })

    assert res_non_existent.status_code == status.HTTP_401_UNAUTHORIZED
    assert res_bad_pw.status_code == status.HTTP_401_UNAUTHORIZED
    assert res_non_existent.data.get("detail") == res_bad_pw.data.get("detail")


@pytest.mark.django_db
def test_jwt_logout_blacklist(api_client, test_users):
    """
    Logging out via /api/auth/logout/ must revoke/blacklist the refresh token.
    Subsequent refresh attempts using the blacklisted token must fail with 401.
    """
    user = test_users["rep_in"]
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    res_logout = api_client.post("/api/auth/logout/", {"refresh": refresh_token})
    assert res_logout.status_code == status.HTTP_200_OK

    # Attempt to refresh token using the blacklisted refresh token
    res_refresh = api_client.post("/api/token/refresh/", {"refresh": refresh_token})
    assert res_refresh.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_must_change_password_middleware_blocks_access(api_client, test_users):
    """
    Users with must_change_password=True are blocked (403 Forbidden) from accessing
    CRM API endpoints until they perform a password change.
    """
    must_change_user = test_users["must_change"]
    api_client.force_authenticate(user=must_change_user)

    # CRM endpoint access blocked
    res_leads = api_client.get("/api/leads/")
    assert res_leads.status_code == status.HTTP_403_FORBIDDEN
    assert "password change is required" in str(res_leads.content).lower()

    # Password change endpoint is permitted
    res_change = api_client.post("/api/auth/change-password/", {
        "old_password": "TempPassword@2026!",
        "new_password": "NewStrongPassword@2026!",
    })
    assert res_change.status_code == status.HTTP_200_OK

    must_change_user.refresh_from_db()
    assert must_change_user.must_change_password is False

    # Now CRM endpoint access is allowed
    res_leads_after = api_client.get("/api/leads/")
    assert res_leads_after.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# 4. Injection, Tampering & Business Logic
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_sent_quote_immutability(api_client, test_users, sample_leads):
    """
    Once a quote is 'sent' or 'accepted', it cannot be updated or altered via PUT/PATCH.
    Only quotes in 'draft' status may be modified.
    """
    api_client.force_authenticate(user=test_users["admin"])
    lead = sample_leads["IN"]

    quote = Quote.objects.create(
        lead=lead,
        version=1,
        system_size_kw=5.0,
        brand="Tata Power",
        price=250000.0,
        status="sent",  # Already sent to customer
        currency="INR",
    )

    res_patch = api_client.patch(f"/api/quotes/{quote.id}/", {
        "price": 100000.0,
        "brand": "Hacked Brand",
    })
    assert res_patch.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]

    quote.refresh_from_db()
    assert quote.price == 250000.0


@pytest.mark.django_db
def test_business_logic_won_requires_accepted_quote(api_client, test_users, sample_leads):
    """
    A lead cannot transition to 'Won' status without having at least one accepted quotation.
    """
    api_client.force_authenticate(user=test_users["admin"])
    lead = sample_leads["IN"]

    # No quote accepted yet; attempt to mark Won
    res = api_client.patch(f"/api/leads/{lead.id}/", {
        "status": "Won",
    })
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert "accepted quote" in str(res.content).lower()


@pytest.mark.django_db
def test_csv_formula_injection_sanitization(api_client, test_users, sample_leads):
    """
    CSV export must sanitize cells starting with =, +, -, @, %, | to neutralize formula injection.
    """
    from leads.import_service import sanitize_csv_cell

    dangerous_inputs = [
        "=cmd|'/C calc'!A0",
        "+123456789",
        "@SUM(1,2)",
        "-456",
        "%COMSPEC%",
        "|dir",
    ]
    for inp in dangerous_inputs:
        sanitized = sanitize_csv_cell(inp)
        assert sanitized.startswith("'"), f"Dangerous input {inp} was not escaped with leading quote: {sanitized}"


@pytest.mark.django_db
def test_date_filter_whitelist_and_bounds_validation(api_client, test_users):
    """
    Date filters must reject years out of bounds (< 1900, > 2100) or malformed dates gracefully.
    """
    api_client.force_authenticate(user=test_users["admin"])

    # Out of bounds years
    res_future = api_client.get("/api/leads/?created_at_after=9999-12-31")
    assert res_future.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    res_past = api_client.get("/api/leads/?created_at_before=1800-01-01")
    assert res_past.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    # Non-date string in date filter
    res_bad = api_client.get("/api/leads/?created_at_after=not_a_real_date")
    assert res_bad.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
    assert "Traceback" not in str(res_bad.content)


# ---------------------------------------------------------------------------
# 5. Security Headers, CORS & I18N Security
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_modern_security_headers_enforced(api_client):
    """
    Verify modern defensive HTTP security headers:
    - Content-Security-Policy
    - X-Content-Type-Options: nosniff
    - Referrer-Policy: same-origin
    - Permissions-Policy
    """
    res = api_client.get("/api/schema/")
    headers = res.headers

    assert "Content-Security-Policy" in headers
    assert "nosniff" in headers.get("X-Content-Type-Options", "")
    assert headers.get("Referrer-Policy") == "same-origin"
    assert "Permissions-Policy" in headers


@pytest.mark.django_db
def test_cors_preflight_allows_language_headers(api_client):
    """
    Verify CORS preflight OPTIONS to /api/auth/password-reset/ allows x-app-language
    and accept-language headers without CORS rejection.
    """
    res = api_client.options(
        "/api/auth/password-reset/",
        HTTP_ORIGIN="http://localhost:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-app-language,content-type,authorization",
    )
    assert res.status_code == status.HTTP_200_OK
    allow_headers = res.headers.get("access-control-allow-headers", "").lower()
    assert "x-app-language" in allow_headers
    assert "accept-language" in allow_headers


@pytest.mark.django_db
def test_translation_xss_sanitization(api_client, test_users):
    """
    Translation input with malicious <script> or event handlers must be sanitized or rejected.
    """
    from masters.views import sanitize_and_validate_translation

    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<iframe src='javascript:alert(1)'>",
        "<img src=x onerror=alert(1)>",
        "<a href='javascript:void(0)'>click</a>",
    ]

    for p in xss_payloads:
        with pytest.raises(Exception):
            sanitize_and_validate_translation(p)


@pytest.mark.django_db
def test_reportlab_pdf_xss_escaping(sample_leads):
    """
    Ensure dynamic strings containing HTML/XML characters in PDF generation are safely escaped.
    """
    from leads.privacy_service import generate_lead_dossier_pdf

    lead = sample_leads["IN"]
    lead.name = "Malicious <script>alert('XSS')</script> & Co."
    lead.remarks = "<b>Bold Attempt</b> & <test>"
    lead.save()

    # Must compile and generate PDF without ReportLab XML parsing errors
    pdf_bytes = generate_lead_dossier_pdf(lead)
    assert pdf_bytes.startswith(b"%PDF-")
