import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from masters.help_service import get_faq_list, query_help_assistant

User = get_user_model()


@pytest.mark.django_db
class TestHelpAssistantService:
    def test_matching_golden_rule(self):
        res = query_help_assistant("What is the golden rule for next follow up date?")
        assert res["matched"] is True
        assert res["id"] == "golden_rule"
        assert "Every call, visit, or interaction must end with an outcome" in res["answer"]
        assert res["action"] is not None

    def test_matching_retry_ladder(self):
        res = query_help_assistant("How does the no answer retry ladder work?")
        assert res["matched"] is True
        assert res["id"] == "retry_ladder"
        assert "Attempt 1" in res["answer"]
        assert "Unreachable" in res["answer"]

    def test_matching_who_can_mark_lost(self):
        res = query_help_assistant("Who can mark a lead as lost?")
        assert res["matched"] is True
        assert res["id"] == "who_can_mark_lost"
        assert "Managers" in res["answer"] and "Admins" in res["answer"]

    def test_matching_csv_import(self):
        res = query_help_assistant("How do I upload or import leads using CSV or excel file?")
        assert res["matched"] is True
        assert res["id"] == "csv_import"
        assert "4-step wizard" in res["answer"]
        assert "Round-Robin" in res["answer"]

    def test_matching_site_surveys(self):
        res = query_help_assistant("Tell me about site technical surveys and roof suitability")
        assert res["matched"] is True
        assert res["id"] == "site_surveys"
        assert "Design pending" in res["answer"]

    def test_matching_quotations(self):
        res = query_help_assistant("How do quotation versions and revisions work?")
        assert res["matched"] is True
        assert res["id"] == "quotations"
        assert "v2" in res["answer"]
        assert "Customer Net Payable" in res["answer"]

    def test_matching_duplicate_merge(self):
        res = query_help_assistant("How to merge duplicate enquiries?")
        assert res["matched"] is True
        assert res["id"] == "lead_dedup"
        assert "Merge Duplicate" in res["answer"]

    def test_query_fallback(self):
        res = query_help_assistant("xyz random unknown question 12345")
        assert res["matched"] is False
        assert "couldn't find an exact match" in res["title"].lower()
        assert len(res["related"]) > 0

    def test_faq_list(self):
        faqs = get_faq_list()
        assert len(faqs) >= 10
        assert any(f["id"] == "golden_rule" for f in faqs)
        assert any(f["id"] == "csv_import" for f in faqs)


@pytest.mark.django_db
class TestHelpAssistantEndpoints:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="help_user",
            password="testpassword123",
            role=User.Role.SALESPERSON,
        )

    def test_help_query_unauthenticated(self):
        response = self.client.post("/api/help/query/", {"query": "How to import CSV?"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_help_query_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/help/query/", {"query": "How to import CSV?"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["matched"] is True
        assert data["id"] == "csv_import"
        assert "wizard" in data["answer"].lower()

    def test_help_query_empty_bad_request(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/help/query/", {"query": "   "})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_help_faqs_list(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/help/faqs/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "faqs" in data
        assert len(data["faqs"]) >= 10
