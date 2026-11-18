import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from ai_assist.context_builder import build_lead_summary_context
from ai_assist.privacy import extract_safe_display_name, sanitize_remark_text
from ai_assist.providers import AnthropicProvider, RulesProvider
from ai_assist.service import get_or_generate_ai_suggestion
from leads.models import AISuggestion, Lead

User = get_user_model()


@pytest.fixture
def sample_lead(db):
    return Lead.objects.create(
        name="Vikramaditya Sharma",
        phone="9876543210",
        alt_phone="9123456789",
        email="vikram.sharma@example.com",
        address="Flat 502, Wing B, Royal Palms, Pune Road",
        city="Pune",
        pincode="411001",
        property_type="Residential",
        roof_type="RCC",
        monthly_bill=4500,
        owner_or_tenant="Owner",
        status=Lead.Status.ATTEMPTING_CONTACT,
        next_action="First call attempt",
        attempt_count=3,
        remark="Customer requested call at Flat 502, phone 9876543210 or email test@solar.org",
    )


@pytest.fixture
def sales_user(db):
    return User.objects.create_user(
        username="sales_vikas",
        password="testpassword123",
        role=User.Role.SALESPERSON,
    )


@pytest.mark.django_db
class TestPrivacyFilter:
    def test_extract_safe_display_name(self):
        assert extract_safe_display_name("Vikramaditya Sharma", 101) == "Vikramaditya"
        assert extract_safe_display_name("A", 102) == "Lead #102"
        assert extract_safe_display_name("9876543210", 103) == "Lead #103"
        assert extract_safe_display_name("", 104) == "Lead #104"

    def test_sanitize_remark_text(self):
        raw = "Call back on 9876543210 or +91 9123456789, email at customer@gmail.com, address Plot 42"
        cleaned = sanitize_remark_text(raw)
        assert "9876543210" not in cleaned
        assert "9123456789" not in cleaned
        assert "customer@gmail.com" not in cleaned
        assert "[PHONE_REDACTED]" in cleaned
        assert "[EMAIL_REDACTED]" in cleaned

    def test_full_context_zero_pii(self, sample_lead):
        context, input_hash = build_lead_summary_context(sample_lead)
        serialized = json.dumps(context)

        # Strict PII Assertions
        assert "9876543210" not in serialized
        assert "9123456789" not in serialized
        assert "vikram.sharma@example.com" not in serialized
        assert "Flat 502, Wing B, Royal Palms, Pune Road" not in serialized
        assert "Vikramaditya Sharma" not in serialized

        # Whitelisted non-PII attributes allowed
        assert context["first_name"] == "Vikramaditya"
        assert context["city"] == "Pune"
        assert context["status"] == Lead.Status.ATTEMPTING_CONTACT
        assert context["attempt_count"] == 3
        assert len(input_hash) == 64


@pytest.mark.django_db
class TestRulesProvider:
    def test_rules_provider_unanswered_calls(self, sample_lead):
        context, _ = build_lead_summary_context(sample_lead)
        provider = RulesProvider()
        result, tokens = provider.generate(context)

        assert tokens == 0
        assert "WhatsApp" in result["best_next_action"]
        assert result["risk_level"] in ["medium", "high"]
        assert len(result["talking_points"]) >= 3
        assert "suggested_whatsapp_message" in result
        assert len(result["objections_to_expect"]) >= 1

    def test_rules_provider_price_concern(self, sample_lead):
        sample_lead.status = Lead.Status.INTERESTED
        sample_lead.save()
        context, _ = build_lead_summary_context(sample_lead)
        # Inject price outcome
        context["recent_activities"] = [{"outcome": "Price or budget concern", "notes": ""}]

        provider = RulesProvider()
        result, _ = provider.generate(context)
        assert "Surya Ghar" in result["talking_points"][0] or "subsidy" in result["best_next_action"].lower()
        assert "payback" in result["best_next_action"].lower() or "subsidy" in result["best_next_action"].lower()


@pytest.mark.django_db
class TestAnthropicProviderMockAndFallback:
    @patch('anthropic.Anthropic')
    def test_anthropic_provider_success(self, mock_anthropic_class, sample_lead):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_content = MagicMock()
        mock_content.type = "text"
        mock_content.text = json.dumps({
            "situation_summary": "Vikramaditya has missed 3 calls. Deal is stalling due to timing.",
            "risk_level": "medium",
            "risk_reason": "Repeated missed calls during work hours.",
            "best_next_action": "Send WhatsApp estimate and propose weekend slot.",
            "suggested_follow_up_timing": "Saturday at 11:00 AM",
            "suggested_outcome_to_log": "Busy or switched off",
            "talking_points": ["Highlight 80% bill reduction", "Confirm roof ownership"],
            "suggested_whatsapp_message": "Namaste Vikramaditya ji! Can I share a quick rooftop savings breakdown here?",
            "objections_to_expect": [{"objection": "Busy now", "reply": "Sure, review when free."}]
        })

        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.usage.input_tokens = 250
        mock_response.usage.output_tokens = 150
        mock_client.messages.create.return_value = mock_response

        provider = AnthropicProvider(api_key="sk-ant-test-key-12345", model="claude-sonnet-5-5")
        context, _ = build_lead_summary_context(sample_lead)
        res, tokens = provider.generate(context)

        assert tokens == 400
        assert res["risk_level"] == "medium"
        assert "Vikramaditya" in res["situation_summary"]

    @patch('anthropic.Anthropic')
    def test_anthropic_invalid_json_fallback(self, mock_anthropic_class, sample_lead, sales_user):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_content = MagicMock()
        mock_content.type = "text"
        mock_content.text = "Sorry, I cannot return JSON right now. Here is some prose..."

        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        with override_settings(AI_PROVIDER="anthropic", ANTHROPIC_API_KEY="sk-ant-test-key"):
            suggestion, is_new = get_or_generate_ai_suggestion(sample_lead, user=sales_user, force_refresh=True)

            assert is_new is True
            # Falls back cleanly to RulesProvider
            assert suggestion.provider == AISuggestion.Provider.RULES
            assert suggestion.is_fallback is True
            assert "Rules Engine (Fallback)" in suggestion.output_json.get("provider_source", "")


@pytest.mark.django_db
class TestCachingAndRateLimiting:
    def test_caching_returns_existing(self, sample_lead, sales_user):
        suggestion1, is_new1 = get_or_generate_ai_suggestion(sample_lead, user=sales_user, force_refresh=False)
        assert is_new1 is True

        suggestion2, is_new2 = get_or_generate_ai_suggestion(sample_lead, user=sales_user, force_refresh=False)
        assert is_new2 is False
        assert suggestion1.id == suggestion2.id
        assert AISuggestion.objects.filter(lead=sample_lead).count() == 1

        # Force refresh creates new record
        suggestion3, is_new3 = get_or_generate_ai_suggestion(sample_lead, user=sales_user, force_refresh=True)
        assert is_new3 is True
        assert suggestion3.id != suggestion1.id

    @patch('anthropic.Anthropic')
    def test_rate_limiting_per_user(self, mock_anthropic_class, sample_lead, sales_user):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_content = MagicMock()
        mock_content.type = "text"
        mock_content.text = json.dumps({
            "situation_summary": "Lead needs follow-up.",
            "risk_level": "low",
            "risk_reason": "Fresh lead.",
            "best_next_action": "Call customer.",
            "suggested_follow_up_timing": "Today",
            "suggested_outcome_to_log": "Interested",
            "talking_points": ["Point 1", "Point 2"],
            "suggested_whatsapp_message": "Hello!",
            "objections_to_expect": []
        })
        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 100
        mock_client.messages.create.return_value = mock_response

        with override_settings(
            AI_PROVIDER="anthropic",
            ANTHROPIC_API_KEY="sk-ant-test-key",
            AI_MAX_CALLS_PER_USER_PER_DAY=2,
        ):
            # Call 1
            s1, _ = get_or_generate_ai_suggestion(sample_lead, user=sales_user, force_refresh=True)
            assert s1.provider == AISuggestion.Provider.ANTHROPIC
            assert s1.is_fallback is False

            # Call 2
            s2, _ = get_or_generate_ai_suggestion(sample_lead, user=sales_user, force_refresh=True)
            assert s2.provider == AISuggestion.Provider.ANTHROPIC
            assert s2.is_fallback is False

            # Call 3 (Exceeds daily max of 2) -> falls back to rules
            s3, _ = get_or_generate_ai_suggestion(sample_lead, user=sales_user, force_refresh=True)
            assert s3.provider == AISuggestion.Provider.RULES
            assert s3.is_fallback is True
            assert "Quota Limit" in s3.output_json.get("provider_source", "")


@pytest.mark.django_db
class TestEndpointsAndDashboard:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="test_coach_user",
            password="testpassword123",
            role=User.Role.MANAGER,
        )

    def test_ai_suggestions_get_and_post_endpoints(self, sample_lead):
        self.client.force_authenticate(user=self.user)

        # GET creates/reads
        get_res = self.client.get(f"/api/leads/{sample_lead.id}/ai-suggestions/")
        assert get_res.status_code == status.HTTP_200_OK
        data = get_res.json()
        assert "suggestion" in data
        assert "situation_summary" in data["suggestion"]["output_json"]

        # POST with refresh
        post_res = self.client.post(f"/api/leads/{sample_lead.id}/ai-suggestions/", {"refresh": True})
        assert post_res.status_code == status.HTTP_200_OK
        assert post_res.json()["is_new"] is True

    def test_dashboard_needs_attention(self, sample_lead):
        self.client.force_authenticate(user=self.user)
        res = self.client.get("/api/dashboard/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "needs_attention" in data
        assert len(data["needs_attention"]) >= 1
        lead_item = next((item for item in data["needs_attention"] if item["id"] == sample_lead.id), None)
        assert lead_item is not None
        assert "failed call attempts" in lead_item["reason"]
