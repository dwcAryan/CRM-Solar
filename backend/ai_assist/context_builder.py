"""
Context builder for Solar CRM AI Assist.
Compiles a compact, sanitized summary of lead history and computes an input hash for cache validation.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from django.utils import timezone

from .privacy import extract_safe_display_name, sanitize_remark_text

if TYPE_CHECKING:
    from leads.models import Lead


def build_lead_summary_context(lead: Lead) -> tuple[dict[str, Any], str]:
    """
    Constructs a compact, privacy-safe dictionary of lead data and history
    and returns (context_dict, input_hash).
    """
    now = timezone.now()
    days_since_created = max(0, (now - lead.created_at).days) if lead.created_at else 0

    safe_first_name = extract_safe_display_name(lead.name, lead.id)

    # 1. Activities (last 20, newest first)
    activities_qs = lead.activities.select_related('outcome').order_by('-created_at')[:20]
    activity_items = []
    latest_activity_id = 0
    for act in activities_qs:
        if not latest_activity_id:
            latest_activity_id = act.id
        activity_items.append({
            "type": act.type,
            "outcome": act.outcome.name if act.outcome else "None",
            "status_after": act.status_after,
            "next_action": act.next_action,
            "remark": sanitize_remark_text(act.remark),
            "notes": sanitize_remark_text(act.notes),
            "days_ago": max(0, (now - act.created_at).days) if act.created_at else 0,
        })

    # 2. Surveys
    surveys_qs = lead.surveys.order_by('-created_at')
    survey_items = []
    latest_survey_status = "none"
    for surv in surveys_qs:
        if latest_survey_status == "none":
            latest_survey_status = f"{surv.id}-{surv.status}"
        survey_items.append({
            "id": surv.id,
            "status": surv.status,
            "site_suitable": surv.site_suitable,
            "reschedule_count": surv.reschedule_count,
            "notes": sanitize_remark_text(surv.notes),
            "remark": sanitize_remark_text(surv.remark),
        })

    # 3. Quotes
    quotes_qs = lead.quotes.order_by('version')
    quote_items = []
    latest_quote_version = 0
    latest_quote_status = "none"
    for q in quotes_qs:
        latest_quote_version = q.version
        latest_quote_status = q.status
        net_price = q.price - (q.subsidy_amount or 0)
        quote_items.append({
            "version": q.version,
            "system_size_kw": q.system_size_kw,
            "brand": q.brand,
            "price": q.price,
            "subsidy_amount": q.subsidy_amount or 0,
            "net_price": net_price,
            "status": q.status,
            "remark": sanitize_remark_text(q.remark),
            "notes": sanitize_remark_text(q.notes),
        })

    # Compact Context Dictionary
    region_code = lead.region_id or "IN"
    region_obj = getattr(lead, 'region', None)

    context: dict[str, Any] = {
        "lead_id": lead.id,
        "first_name": safe_first_name,
        "region": region_code,
        "region_name": region_obj.name if region_obj else ("Australia" if region_code == "AU" else "India"),
        "currency": region_obj.currency if region_obj else ("AUD" if region_code == "AU" else "INR"),
        "currency_symbol": region_obj.currency_symbol if region_obj else ("A$" if region_code == "AU" else "₹"),
        "incentive_label": region_obj.incentive_label if region_obj else ("Government incentive (STCs and rebates)" if region_code == "AU" else "Subsidy"),
        "electricity_provider_label": region_obj.electricity_provider_label if region_obj else ("Electricity retailer" if region_code == "AU" else "DISCOM"),
        "preferred_channels": region_obj.preferred_channels if region_obj else ("sms,whatsapp" if region_code == "AU" else "whatsapp,sms"),
        "region_notes": region_obj.region_notes if region_obj else "",
        "state": lead.state or "",
        "city": lead.city or ("Sydney" if region_code == "AU" else "Ahmedabad"),
        "suburb": lead.suburb or "",
        "timezone": lead.timezone or (region_obj.default_timezone if region_obj else "Asia/Kolkata"),
        "status": lead.status,
        "next_action": lead.next_action or "Not set",
        "next_followup_at": lead.next_followup_at.isoformat() if lead.next_followup_at else None,
        "source": lead.source.name if lead.source else "Direct",
        "property_type": lead.property_type or "Residential",
        "monthly_bill": lead.monthly_bill,
        "bill_amount": float(lead.bill_amount) if lead.bill_amount else None,
        "bill_period": lead.bill_period or "monthly",
        "normalized_monthly_bill": float(lead.normalized_monthly_bill) if lead.normalized_monthly_bill else (float(lead.monthly_bill) if lead.monthly_bill else None),
        "electricity_provider": lead.electricity_provider or "",
        "roof_type": lead.roof_type or ("Colorbond" if region_code == "AU" else "RCC"),
        "owner_or_tenant": lead.owner_or_tenant or "Owner",
        "days_since_created": days_since_created,
        "attempt_count": lead.attempt_count,
        "lost_reason": lead.lost_reason.name if lead.lost_reason else None,
        "nurture_reason": lead.nurture_reason.name if lead.nurture_reason else None,
        "activities_count": len(activity_items),
        "recent_activities": activity_items,
        "surveys": survey_items,
        "quotes": quote_items,
    }

    # Generate a deterministic input hash based on critical state components
    hash_payload = {
        "status": lead.status,
        "next_action": lead.next_action,
        "next_followup_at": lead.next_followup_at.isoformat() if lead.next_followup_at else "",
        "attempt_count": lead.attempt_count,
        "lost_reason": lead.lost_reason_id,
        "nurture_reason": lead.nurture_reason_id,
        "latest_activity_id": latest_activity_id,
        "activities_len": len(activity_items),
        "latest_survey_status": latest_survey_status,
        "latest_quote_version": latest_quote_version,
        "latest_quote_status": latest_quote_status,
    }
    hash_str = json.dumps(hash_payload, sort_keys=True)
    input_hash = hashlib.sha256(hash_str.encode('utf-8')).hexdigest()

    return context, input_hash
