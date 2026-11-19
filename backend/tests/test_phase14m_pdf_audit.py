"""
Regression & Specification Tests for PDF Features (Phase 14M Audit).
Tests written BEFORE fixes according to Phase 14M requirements:
- Privacy DSAR Dossier PDF (A4 size, Unicode support, RFC 5987, Cache-Control: private, no-store)
- Solar Quotation PDF (A4 size, Line items, Indian CGST/SGST & Australian GST 10%, Payment terms, Bank details, Signatures, RFC 5987)
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from leads.models import Lead
from masters.models import Region, State
from quotes.models import Quote
from tests.pdf_utils import assert_pdf_valid, assert_private_pdf_response


@pytest.fixture
def pdf_test_setup(db):
    region_in, _ = Region.objects.get_or_create(
        code='IN',
        defaults={
            'name': 'India',
            'currency': 'INR',
            'currency_symbol': '₹',
            'tax_rate': 0.0500,
            'incentive_label': 'PM Surya Ghar Subsidy',
        },
    )
    region_au, _ = Region.objects.get_or_create(
        code='AU',
        defaults={
            'name': 'Australia',
            'currency': 'AUD',
            'currency_symbol': 'A$',
            'tax_rate': 0.1000,
            'incentive_label': 'STC Solar Rebate',
        },
    )

    state_mh, _ = State.objects.get_or_create(
        code='MH',
        region=region_in,
        defaults={'name': 'Maharashtra'},
    )
    state_nsw, _ = State.objects.get_or_create(
        code='NSW',
        region=region_au,
        defaults={'name': 'New South Wales'},
    )

    admin_user = User.objects.create_user(
        username='pdf_admin_user',
        email='pdf_admin@example.com',
        password='TestPassword123!',
        role=User.Role.ADMIN,
    )
    admin_user.allowed_regions.add(region_in, region_au)

    sales_user = User.objects.create_user(
        username='pdf_sales_user',
        email='pdf_sales@example.com',
        password='TestPassword123!',
        role=User.Role.SALESPERSON,
    )
    sales_user.allowed_regions.add(region_in, region_au)

    lead_in = Lead.objects.create(
        name='राजेश कुमार शर्मा',
        phone='+919876543210',
        email='rajesh.sharma@example.in',
        region=region_in,
        state=state_mh,
        monthly_bill=5000,
        assigned_to=sales_user,
    )

    lead_au = Lead.objects.create(
        name='John O\'Connor & Sons',
        phone='+61412345678',
        email='john.oconnor@example.com.au',
        region=region_au,
        state=state_nsw,
        monthly_bill=350,
        assigned_to=sales_user,
    )

    return {
        'admin_user': admin_user,
        'sales_user': sales_user,
        'region_in': region_in,
        'region_au': region_au,
        'lead_in': lead_in,
        'lead_au': lead_au,
    }


@pytest.mark.django_db
def test_privacy_dossier_pdf_audit_requirements(pdf_test_setup):
    """
    Audit Test: Privacy dossier PDF must:
    1. Render in standard A4 format (not letter).
    2. Support Unicode characters (Hindi names, Rupee symbol ₹).
    3. Return Cache-Control: private, no-store.
    4. Provide RFC 5987 encoded Content-Disposition header.
    5. Be restricted to Administrators.
    """
    admin_user = pdf_test_setup['admin_user']
    sales_user = pdf_test_setup['sales_user']
    lead = pdf_test_setup['lead_in']

    # 1. Non-admin forbidden
    sales_client = APIClient()
    sales_client.force_authenticate(user=sales_user)
    res_forbidden = sales_client.get(f'/api/leads/{lead.id}/privacy-export/?format=pdf')
    assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN

    # 2. Admin export
    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)
    res = admin_client.get(f'/api/leads/{lead.id}/privacy-export/?format=pdf')

    pdf_bytes = assert_private_pdf_response(res, expected_filename_substr='privacy_dossier')

    # Verify A4 size and Hindi/Rupee extractable text
    assert_pdf_valid(
        pdf_bytes,
        expected_substrings=['राजेश कुमार शर्मा', 'Privacy Data Dossier'],
        check_a4=True,
    )


@pytest.mark.django_db
def test_quote_pdf_audit_requirements_india(pdf_test_setup):
    """
    Audit Test: India Quotation PDF must:
    1. Render on standard A4 paper size.
    2. Display CGST and SGST breakdown (for intra-state GST).
    3. Display subsidy incentive deduction (PM Surya Ghar).
    4. Include payment terms and bank details.
    5. Include multi-currency formatting with '₹'.
    6. Return RFC 5987 Content-Disposition and Cache-Control: private, no-store.
    """
    admin_user = pdf_test_setup['admin_user']
    lead = pdf_test_setup['lead_in']

    quote = Quote.objects.create(
        lead=lead,
        brand='Tata Power Solar 5kW High Efficiency',
        system_size_kw=5.0,
        price=250000.00,
        subsidy_amount=78000.00,
        created_by=admin_user,
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)
    res = client.get(f'/api/quotes/{quote.id}/pdf/')

    pdf_bytes = assert_private_pdf_response(res, expected_filename_substr='quote_')

    assert_pdf_valid(
        pdf_bytes,
        expected_substrings=[
            'Solar CRM Quotation',
            'Tata Power Solar',
            '5.00 kW',
            'CGST',
            'SGST',
            'Bank Details',
            'Payment Terms',
            'Authorized Signatory',
        ],
        check_a4=True,
    )


@pytest.mark.django_db
def test_quote_pdf_audit_requirements_australia(pdf_test_setup):
    """
    Audit Test: Australia Quotation PDF must:
    1. Render on standard A4 paper size.
    2. Display Australia GST (10%) and STC solar rebate incentive.
    3. Display A$ currency.
    4. Include payment terms, bank details, and customer signature block.
    """
    admin_user = pdf_test_setup['admin_user']
    lead = pdf_test_setup['lead_au']

    quote = Quote.objects.create(
        lead=lead,
        brand='Fronius + REC 6.6kW Commercial',
        system_size_kw=6.6,
        price=7500.00,
        battery_kwh=10.0,
        subsidy_amount=2200.00,
        created_by=admin_user,
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)
    res = client.get(f'/api/quotes/{quote.id}/pdf/')

    pdf_bytes = assert_private_pdf_response(res, expected_filename_substr='quote_')

    assert_pdf_valid(
        pdf_bytes,
        expected_substrings=[
            'Solar CRM Quotation',
            'Fronius + REC',
            '6.60 kW',
            'GST (10%)',
            'STC',
            'A$',
            'Bank Details',
            'Customer Signature',
        ],
        check_a4=True,
    )
