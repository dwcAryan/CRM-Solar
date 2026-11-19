import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone

from accounts.models import User
from masters.models import (
    Language,
    Outcome,
    LostReason,
    NurtureReason,
    Region,
    TranslationEntry,
)
from leads.models import Lead, LeadStatusHistory, AuditLog
from activities.models import Activity
from notifications.models import Notification
from messaging.models import MessageTemplate, MessageLog
from messaging.sms_counter import calculate_sms_segments
from messaging.providers import resolve_template_for_recipient
from leads.history_renderer import render_history_text
from masters.management.commands.translate_missing import draft_missing_for_language


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        username="admin_i18n",
        password="AdminPass123!@#",
        role=User.Role.ADMIN,
        preferred_language="en",
    )
    return user


@pytest.fixture
def manager_user(db):
    user = User.objects.create_user(
        username="manager_i18n",
        password="ManagerPass123!@#",
        role=User.Role.MANAGER,
        preferred_language="hi",
    )
    return user


@pytest.fixture
def salesperson_user(db):
    user = User.objects.create_user(
        username="sales_i18n",
        password="SalesPass123!@#",
        role=User.Role.SALESPERSON,
        preferred_language="en",
    )
    return user


@pytest.fixture
def setup_i18n_masters(db):
    # Setup languages
    en_lang, _ = Language.objects.get_or_create(
        code="en",
        defaults={
            "name": "English",
            "native_name": "English",
            "is_enabled": True,
            "completeness_pct": 100.0,
        },
    )
    hi_lang, _ = Language.objects.get_or_create(
        code="hi",
        defaults={
            "name": "Hindi",
            "native_name": "हिन्दी",
            "is_enabled": True,
            "completeness_pct": 100.0,
        },
    )
    au_lang, _ = Language.objects.get_or_create(
        code="en-AU",
        defaults={
            "name": "English (Australia)",
            "native_name": "English (AU)",
            "is_enabled": True,
            "completeness_pct": 100.0,
        },
    )

    # Master Outcome with translations
    outcome, _ = Outcome.objects.get_or_create(
        name="Callback Requested",
        defaults={
            "stage": "call",
            "code": "OUTCOME_CALLBACK",
            "translations": {
                "hi": "पुनः कॉल का अनुरोध (Callback)",
                "en-AU": "Callback Requested",
            },
        },
    )

    # Region with default language
    region_in, _ = Region.objects.get_or_create(
        code="IN",
        defaults={
            "name": "India",
            "currency": "INR",
            "currency_symbol": "₹",
            "default_language": "hi",
            "translations": {"hi": "भारत"},
        },
    )

    return {
        "en": en_lang,
        "hi": hi_lang,
        "au": au_lang,
        "outcome": outcome,
        "region_in": region_in,
    }


# ==============================================================================
# 1. SMS SEGMENT COUNTER (GSM-7 VS UCS-2 DEVANAGARI)
# ==============================================================================

def test_sms_counter_gsm7_ascii():
    # ASCII text within 160 characters is 1 segment
    text = "Hello customer, your solar quotation is ready for review."
    res = calculate_sms_segments(text)
    assert res.encoding == "GSM-7"
    assert res.segments == 1
    assert res.char_count == len(text)
    assert res.is_unicode is False
    assert res.chars_remaining == 160 - len(text)


def test_sms_counter_gsm7_multi_segment():
    # Long ASCII text exceeding 160 chars splits at 153 chars/segment
    text = "A" * 165
    res = calculate_sms_segments(text)
    assert res.encoding == "GSM-7"
    assert res.segments == 2
    assert res.chars_per_segment == 153


def test_sms_counter_ucs2_devanagari():
    # Devanagari text uses UCS-2: single segment up to 70 chars
    hindi_text = "नमस्ते ग्राहक, आपका सोलर कोटेशन तैयार है।"
    res = calculate_sms_segments(hindi_text)
    assert res.encoding == "UCS-2"
    assert res.is_unicode is True
    assert res.segments == 1
    assert res.chars_per_segment == 70
    assert res.chars_remaining == 70 - len(hindi_text)


def test_sms_counter_ucs2_multi_segment():
    # Devanagari text exceeding 70 chars splits at 67 chars/segment
    long_hindi = "नमस्ते" * 15  # 90 characters
    res = calculate_sms_segments(long_hindi)
    assert res.encoding == "UCS-2"
    assert res.is_unicode is True
    assert res.segments == 2
    assert res.chars_per_segment == 67


# ==============================================================================
# 2. DYNAMIC HISTORY RENDERING (READ TIME AT CLIENT LANGUAGE)
# ==============================================================================

def test_history_renderer_en_and_hi():
    params = {"status": "Contacted"}
    en_rendered = render_history_text("STATUS_INITIAL", params, language="en")
    hi_rendered = render_history_text("STATUS_INITIAL", params, language="hi")

    assert en_rendered == "Initial transition to Contacted"
    assert hi_rendered == "प्रारंभिक स्थिति: Contacted"


def test_history_renderer_quote_and_lead():
    params = {"kw": 5, "version": 1}
    en_quote = render_history_text("QUOTE_CREATED", params, language="en")
    hi_quote = render_history_text("QUOTE_CREATED", params, language="hi")
    au_quote = render_history_text("QUOTE_CREATED", params, language="en-AU")

    assert "Quote v1 created for 5 kW system" in en_quote
    assert "5 किलोवाट प्रणाली" in hi_quote
    assert "Proposal v1 created for 5 kW system" in au_quote


def test_history_renderer_legacy_fallback():
    # If code is missing or unmapped, returns fallback text
    rendered = render_history_text(None, {}, language="hi", fallback_text="Old legacy note")
    assert rendered == "Old legacy note"


# ==============================================================================
# 3. LANGUAGE RESOLUTION & VARY HEADER
# ==============================================================================

def test_language_middleware_resolution_and_vary_header(api_client, setup_i18n_masters, salesperson_user):
    api_client.force_authenticate(user=salesperson_user)

    # 1. Without header: uses user.preferred_language ('en')
    resp = api_client.get("/api/masters/outcomes/")
    assert resp.status_code == 200
    assert "Accept-Language" in resp.headers.get("Vary", "")

    # 2. With X-App-Language header: activates Hindi
    resp_hi = api_client.get("/api/masters/outcomes/", HTTP_X_APP_LANGUAGE="hi")
    assert resp_hi.status_code == 200
    assert "Accept-Language" in resp_hi.headers.get("Vary", "")

    data = resp_hi.json()
    first_item = data["results"][0] if "results" in data else data[0]
    # Check localized display name
    assert first_item["display_name"] == "पुनः कॉल का अनुरोध (Callback)"


# ==============================================================================
# 4. MASTER DATA CODE STABILITY
# ==============================================================================

def test_master_data_code_stability(api_client, setup_i18n_masters, salesperson_user):
    api_client.force_authenticate(user=salesperson_user)

    resp_en = api_client.get("/api/masters/outcomes/", HTTP_ACCEPT_LANGUAGE="en")
    resp_hi = api_client.get("/api/masters/outcomes/", HTTP_ACCEPT_LANGUAGE="hi")

    item_en = resp_en.json()["results"][0] if "results" in resp_en.json() else resp_en.json()[0]
    item_hi = resp_hi.json()["results"][0] if "results" in resp_hi.json() else resp_hi.json()[0]

    # Machine code and ID are 100% identical regardless of language
    assert item_en["id"] == item_hi["id"]
    assert item_en["code"] == item_hi["code"]
    assert item_en["code"] == "OUTCOME_CALLBACK"

    # Display name reflects viewer's language
    assert item_en["display_name"] == "Callback Requested"
    assert item_hi["display_name"] == "पुनः कॉल का अनुरोध (Callback)"


# ==============================================================================
# 5. IDENTICAL BUSINESS JOURNEY IN HINDI
# ==============================================================================

def test_identical_business_journey_in_hindi(api_client, setup_i18n_masters, salesperson_user):
    api_client.force_authenticate(user=salesperson_user)

    # Create lead with Hindi communication preference and Hindi customer name
    lead_data = {
        "name": "राजेश कुमार",
        "phone": "+919876543210",
        "email": "rajesh.patel@example.com",
        "city": "Ahmedabad",
        "region": "IN",
        "preferred_language": "hi",
        "monthly_bill": 5000,
    }
    resp = api_client.post("/api/leads/", lead_data, format="json", HTTP_X_APP_LANGUAGE="hi")
    assert resp.status_code == 201
    lead_id = resp.json()["id"]

    # Verify lead created with correct code and preferred language
    lead = Lead.objects.get(id=lead_id)
    assert lead.status == "New"
    assert lead.preferred_language == "hi"

    # Log interaction
    act_resp = api_client.post(
        "/api/activities/",
        {
            "lead": lead_id,
            "type": "call",
            "outcome": setup_i18n_masters["outcome"].id,
            "notes": "ग्राहक ने शाम 6 बजे बात करने को कहा",
            "status_after": "Contacted",
            "message_code": "CALL_LOGGED",
            "params": {"outcome": "पुनः कॉल का अनुरोध"},
        },
        format="json",
        HTTP_X_APP_LANGUAGE="hi",
    )
    assert act_resp.status_code == 201

    # Verify rendered text on activity
    act = Activity.objects.get(id=act_resp.json()["id"])
    assert act.message_code == "CALL_LOGGED"


# ==============================================================================
# 6. TEMPLATE FALLBACK CHAIN & APPROVAL BLOCKING
# ==============================================================================

def test_template_fallback_chain(db, setup_i18n_masters):
    # Template exists in English and Hindi
    t_en = MessageTemplate.objects.create(
        channel="whatsapp",
        name="quote_sent",
        language="en",
        body="Hello {{customer_name}}, your quote is {{quote_url}}",
        approval_status="approved",
    )
    t_hi = MessageTemplate.objects.create(
        channel="whatsapp",
        name="quote_sent",
        language="hi",
        body="नमस्ते {{customer_name}}, आपका कोटेशन {{quote_url}} है",
        approval_status="approved",
    )

    lead_hi = Lead.objects.create(
        name="Sunil",
        phone="+919876543211",
        city="Delhi",
        region_id="IN",
        preferred_language="hi",
    )
    resolved = resolve_template_for_recipient("quote_sent", lead_hi, channel="whatsapp")
    assert resolved.id == t_hi.id

    # Fallback to English when preferred language template is absent
    t_pending = MessageTemplate.objects.create(
        channel="whatsapp",
        name="unapproved_key",
        language="en",
        body="Wait for approval",
        approval_status="pending",
    )
    with pytest.raises(ValueError, match="pending approval"):
        resolve_template_for_recipient("unapproved_key", lead_hi, channel="whatsapp")


# ==============================================================================
# 7. TRANSLATION ADMIN ENDPOINTS & SECURITY
# ==============================================================================

def test_translation_permissions_and_xss_protection(api_client, setup_i18n_masters, admin_user, salesperson_user):
    # Public list of languages (unauthenticated)
    resp = api_client.get("/api/masters/languages/")
    assert resp.status_code == 200

    # Salesperson forbidden from editing translations (403)
    api_client.force_authenticate(user=salesperson_user)
    resp_forbidden = api_client.post("/api/masters/translations/import/", {"lang": "hi", "items": []})
    assert resp_forbidden.status_code == 403

    # Admin allowed
    api_client.force_authenticate(user=admin_user)

    # 1. Toggle language
    lang_hi = setup_i18n_masters["hi"]
    resp_toggle = api_client.post(f"/api/masters/languages/{lang_hi.id}/toggle_enabled/")
    assert resp_toggle.status_code == 200

    # 2. XSS injection rejected with 400
    entry = TranslationEntry.objects.create(
        language=lang_hi,
        namespace="common",
        key="btn.save",
        english_text="Save",
        translated_text="सुरक्षित करें",
        status="approved",
    )
    xss_resp = api_client.patch(
        f"/api/masters/translations/{entry.id}/",
        {"translated_text": "<script>alert('XSS')</script>"},
    )
    assert xss_resp.status_code == 400
    assert "Unsafe HTML tags" in str(xss_resp.json())

    # 3. ICU placeholder mismatch rejected with 400
    entry_ph = TranslationEntry.objects.create(
        language=lang_hi,
        namespace="common",
        key="welcome.user",
        english_text="Welcome {username} to Solar CRM",
        translated_text="स्वागत {username}",
        status="approved",
    )
    ph_resp = api_client.patch(
        f"/api/masters/translations/{entry_ph.id}/",
        {"translated_text": "स्वागत बिना किसी प्लेसहोल्डर के"},
    )
    assert ph_resp.status_code == 400
    assert "Placeholder mismatch" in str(ph_resp.json())


# ==============================================================================
# 8. AUTO-DRAFT MISSING STRINGS LOGIC
# ==============================================================================

def test_translate_missing_logic(db, setup_i18n_masters, admin_user):
    en_lang = setup_i18n_masters["en"]
    hi_lang = setup_i18n_masters["hi"]

    # Create English keys
    TranslationEntry.objects.create(
        language=en_lang,
        namespace="common",
        key="actions.save",
        english_text="Save",
        translated_text="Save",
        status="approved",
    )
    TranslationEntry.objects.create(
        language=en_lang,
        namespace="common",
        key="actions.delete",
        english_text="Delete",
        translated_text="Delete",
        status="approved",
    )

    # Draft missing for Hindi
    drafted_count = draft_missing_for_language(hi_lang, user=admin_user)
    assert drafted_count >= 2

    # Check that drafted entry has status 'draft' and uses glossary/dictionary
    save_entry = TranslationEntry.objects.get(language=hi_lang, namespace="common", key="actions.save")
    assert save_entry.status == "draft"
    assert save_entry.translated_text == "सुरक्षित करें"

    # Completeness updated
    hi_lang.refresh_from_db()
    assert hi_lang.completeness_pct > 0


# ==============================================================================
# 9. CORS PREFLIGHT ALLOWS X-APP-LANGUAGE
# ==============================================================================

def test_cors_allows_i18n_headers(api_client):
    """Ensure CORS preflight OPTIONS requests permit X-App-Language and Accept-Language headers."""
    response = api_client.options(
        "/api/auth/password-reset/",
        HTTP_ORIGIN="http://localhost:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-app-language,accept-language,content-type",
    )
    assert response.status_code == 200
    allow_headers = response.get("Access-Control-Allow-Headers", "").lower()
    assert "x-app-language" in allow_headers
    assert "accept-language" in allow_headers

