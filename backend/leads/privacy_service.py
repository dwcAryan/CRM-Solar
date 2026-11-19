"""
Privacy & Compliance Service for Solar CRM.
Implements:
1. Data Subject Access Request (DSAR) export as JSON or PDF dossier.
2. Irreversible data anonymization / right-to-be-forgotten.
3. Data rectification / correction with mandatory audit trail.
"""

from __future__ import annotations

import html
import io
from typing import TYPE_CHECKING, Any, Dict, Optional

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import AuditLog, Lead
from .phone_utils import normalize_phone_number
from .timezone_utils import format_datetime_in_timezone

if TYPE_CHECKING:
    from accounts.models import User


def generate_lead_dossier_dict(lead: Lead) -> Dict[str, Any]:
    """
    Assembles complete, structured JSON dossier for a lead, including all related
    activities, surveys, quotes, status history, and compliance audit entries.
    """
    tz = lead.timezone or (lead.region.default_timezone if lead.region else 'Asia/Kolkata')

    activities = []
    for act in lead.activities.select_related('outcome', 'created_by').order_by('created_at'):
        activities.append({
            'id': act.id,
            'type': act.type,
            'outcome': act.outcome.name if act.outcome else None,
            'status_after': act.status_after,
            'next_action': act.next_action,
            'next_followup_at': format_datetime_in_timezone(act.next_followup_at, tz),
            'notes': act.notes,
            'remark': act.remark,
            'created_by': act.created_by.get_full_name() if act.created_by else 'System',
            'created_at': format_datetime_in_timezone(act.created_at, tz),
        })

    surveys = []
    for surv in lead.surveys.select_related('surveyor').order_by('scheduled_at'):
        surveys.append({
            'id': surv.id,
            'status': surv.status,
            'scheduled_at': format_datetime_in_timezone(surv.scheduled_at, tz),
            'site_suitable': surv.site_suitable,
            'notes': surv.notes,
            'remark': surv.remark,
            'surveyor': surv.surveyor.get_full_name() if surv.surveyor else None,
            'reschedule_count': surv.reschedule_count,
        })

    quotes = []
    for q in lead.quotes.order_by('version'):
        quotes.append({
            'id': q.id,
            'version': q.version,
            'system_size_kw': float(q.system_size_kw),
            'brand': q.brand,
            'price': float(q.price),
            'currency': q.currency or ('INR' if q.region_id == 'IN' else 'AUD'),
            'tax_rate': float(q.tax_rate) if q.tax_rate is not None else None,
            'tax_amount': float(q.tax_amount) if q.tax_amount is not None else None,
            'incentive_label': q.incentive_label,
            'incentive_amount': float(q.incentive_amount or q.subsidy_amount or 0),
            'battery_kwh': float(q.battery_kwh) if q.battery_kwh else None,
            'status': q.status,
            'created_at': format_datetime_in_timezone(q.created_at, tz),
        })

    status_history = []
    for sh in lead.status_history.select_related('changed_by').order_by('changed_at'):
        status_history.append({
            'id': sh.id,
            'old_status': sh.old_status,
            'new_status': sh.new_status,
            'changed_by': sh.changed_by.get_full_name() if sh.changed_by else 'System',
            'changed_at': format_datetime_in_timezone(sh.changed_at, tz),
            'note': sh.note,
            'remark': sh.remark,
        })

    audit_logs = []
    for al in AuditLog.objects.filter(lead_id_recorded=lead.id).order_by('timestamp'):
        audit_logs.append({
            'id': al.id,
            'action': al.action,
            'user': al.user_name or 'System',
            'timestamp': format_datetime_in_timezone(al.timestamp, tz),
            'reason': al.reason,
            'details': al.details,
            'ip_address': al.ip_address,
        })

    return {
        'export_metadata': {
            'generated_at': format_datetime_in_timezone(timezone.now(), tz),
            'lead_id': lead.id,
            'compliance_context': f"Privacy / DSAR Dossier ({lead.region_id or 'IN'})",
        },
        'lead_profile': {
            'id': lead.id,
            'name': lead.name,
            'phone': lead.phone_e164 or lead.phone,
            'alt_phone': lead.alt_phone_e164 or lead.alt_phone,
            'email': lead.email,
            'address': lead.address,
            'city': lead.city,
            'suburb': lead.suburb,
            'state': lead.state,
            'pincode': lead.pincode,
            'postcode': lead.postcode,
            'region': lead.region_id,
            'timezone': tz,
            'status': lead.status,
            'next_action': lead.next_action,
            'next_followup_at': format_datetime_in_timezone(lead.next_followup_at, tz),
            'source': lead.source.name if lead.source else None,
            'assigned_to': lead.assigned_to.get_full_name() if lead.assigned_to else 'Unassigned',
            'created_at': format_datetime_in_timezone(lead.created_at, tz),
            'updated_at': format_datetime_in_timezone(lead.updated_at, tz),
            'won_at': format_datetime_in_timezone(lead.won_at, tz) if lead.won_at else None,
        },
        'consent_and_compliance': {
            'consent_status': lead.consent_status,
            'consent_source': lead.consent_source,
            'consent_date': lead.consent_date.isoformat() if lead.consent_date else None,
            'do_not_contact': lead.do_not_contact,
            'opt_out_calls': lead.opt_out_calls,
            'opt_out_sms': lead.opt_out_sms,
            'opt_out_whatsapp': lead.opt_out_whatsapp,
            'opt_out_email': lead.opt_out_email,
            'dncr_status': lead.dncr_status,
            'dncr_checked_at': format_datetime_in_timezone(lead.dncr_checked_at, tz) if lead.dncr_checked_at else None,
            'dncr_checked_by': lead.dncr_checked_by.get_full_name() if lead.dncr_checked_by else None,
        },
        'energy_and_property': {
            'property_type': lead.property_type,
            'roof_type': lead.roof_type,
            'owner_or_tenant': lead.owner_or_tenant,
            'bill_amount': float(lead.bill_amount) if lead.bill_amount else None,
            'bill_period': lead.bill_period,
            'normalized_monthly_bill': float(lead.normalized_monthly_bill) if lead.normalized_monthly_bill else None,
            'electricity_provider': lead.electricity_provider,
        },
        'activities': activities,
        'surveys': surveys,
        'quotes': quotes,
        'status_history': status_history,
        'compliance_audit_logs': audit_logs,
    }


def generate_lead_dossier_pdf(lead: Lead) -> bytes:
    """
    Generates a clean, professional PDF dossier using ReportLab.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    dossier = generate_lead_dossier_dict(lead)
    profile = dossier['lead_profile']
    compliance = dossier['consent_and_compliance']
    energy = dossier['energy_and_property']

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=4,
    )
    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2b6cb0'),
        spaceBefore=12,
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        'MetaStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#4a5568'),
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
    )
    bold_cell_style = ParagraphStyle(
        'TableBoldCell',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2d3748'),
    )

    def safe_p(text: Any, style=cell_style) -> Paragraph:
        val = "" if text is None else str(text)
        return Paragraph(html.escape(val), style)

    elements = []

    # Title & Header
    elements.append(Paragraph("Privacy Data Dossier / DSAR Export", title_style))
    escaped_name = html.escape(str(profile['name'] or 'N/A'))
    escaped_region = html.escape(str(profile['region'] or 'N/A'))
    escaped_gen = html.escape(str(dossier['export_metadata']['generated_at']))
    elements.append(Paragraph(
        f"<b>Subject:</b> {escaped_name} (Lead #{profile['id']}) | "
        f"<b>Region:</b> {escaped_region} | "
        f"<b>Exported:</b> {escaped_gen}",
        meta_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2b6cb0'), spaceBefore=8, spaceAfter=10))

    # Section 1: Personal Profile
    elements.append(Paragraph("1. Personal & Contact Identifiers", h2_style))
    profile_data = [
        [Paragraph("Full Name", bold_cell_style), safe_p(profile['name'] or 'N/A'),
         Paragraph("Lead ID", bold_cell_style), safe_p(profile['id']),],
        [Paragraph("Primary Phone (E.164)", bold_cell_style), safe_p(profile['phone'] or 'N/A'),
         Paragraph("Alt Phone", bold_cell_style), safe_p(profile['alt_phone'] or 'N/A')],
        [Paragraph("Email", bold_cell_style), safe_p(profile['email'] or 'N/A'),
         Paragraph("Current Status", bold_cell_style), safe_p(profile['status'] or 'N/A')],
        [Paragraph("Address", bold_cell_style), safe_p(profile['address'] or 'N/A'),
         Paragraph("City / Suburb", bold_cell_style), safe_p(f"{profile['city'] or ''} {profile['suburb'] or ''}".strip() or 'N/A')],
        [Paragraph("State / Territory", bold_cell_style), safe_p(profile['state'] or 'N/A'),
         Paragraph("Pincode / Postcode", bold_cell_style), safe_p(profile['postcode'] or profile['pincode'] or 'N/A')],
        [Paragraph("Timezone", bold_cell_style), safe_p(profile['timezone']),
         Paragraph("Assigned Salesperson", bold_cell_style), safe_p(profile['assigned_to'])],
    ]
    t1 = Table(profile_data, colWidths=[130, 140, 130, 140])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t1)

    # Section 2: Consent & Opt-Outs
    elements.append(Paragraph("2. Consent & Communication Preferences", h2_style))
    consent_data = [
        [Paragraph("Consent Status", bold_cell_style), safe_p(compliance['consent_status']),
         Paragraph("Consent Source", bold_cell_style), safe_p(compliance['consent_source'])],
        [Paragraph("Consent Date", bold_cell_style), safe_p(compliance['consent_date'] or 'N/A'),
         Paragraph("Do Not Contact (Global)", bold_cell_style), safe_p("YES (BLOCKED)" if compliance['do_not_contact'] else "No")],
        [Paragraph("Opt-out Calls", bold_cell_style), safe_p("Yes" if compliance['opt_out_calls'] else "No"),
         Paragraph("Opt-out SMS", bold_cell_style), safe_p("Yes" if compliance['opt_out_sms'] else "No")],
        [Paragraph("Opt-out WhatsApp", bold_cell_style), safe_p("Yes" if compliance['opt_out_whatsapp'] else "No"),
         Paragraph("Opt-out Email", bold_cell_style), safe_p("Yes" if compliance['opt_out_email'] else "No")],
        [Paragraph("DNCR Status", bold_cell_style), safe_p(compliance['dncr_status']),
         Paragraph("DNCR Checked At", bold_cell_style), safe_p(compliance['dncr_checked_at'] or 'Never')],
    ]
    t2 = Table(consent_data, colWidths=[130, 140, 130, 140])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#edf2f7')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t2)

    # Section 3: Energy & Property
    elements.append(Paragraph("3. Energy & Rooftop Characteristics", h2_style))
    energy_data = [
        [Paragraph("Property Type", bold_cell_style), safe_p(energy['property_type'] or 'N/A'),
         Paragraph("Roof Type", bold_cell_style), safe_p(energy['roof_type'] or 'N/A')],
        [Paragraph("Occupancy", bold_cell_style), safe_p(energy['owner_or_tenant'] or 'N/A'),
         Paragraph("Electricity Provider", bold_cell_style), safe_p(energy['electricity_provider'] or 'N/A')],
        [Paragraph("Recorded Bill", bold_cell_style), safe_p(f"{energy['bill_amount']} ({energy['bill_period']})" if energy['bill_amount'] else 'N/A'),
         Paragraph("Normalized Monthly Bill", bold_cell_style), safe_p(f"{energy['normalized_monthly_bill']}" if energy['normalized_monthly_bill'] else 'N/A')],
    ]
    t3 = Table(energy_data, colWidths=[130, 140, 130, 140])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t3)

    # Section 4: Activities Summary
    elements.append(Paragraph(f"4. Recorded Interactions ({len(dossier['activities'])} total)", h2_style))
    if dossier['activities']:
        act_rows = [[
            Paragraph("Timestamp", bold_cell_style),
            Paragraph("Type", bold_cell_style),
            Paragraph("Outcome", bold_cell_style),
            Paragraph("Next Action", bold_cell_style),
            Paragraph("Logged By", bold_cell_style),
        ]]
        for a in dossier['activities'][:15]:  # Top 15
            act_rows.append([
                safe_p(a['created_at']),
                safe_p(a['type'].upper()),
                safe_p(a['outcome'] or '-'),
                safe_p(a['next_action'] or '-'),
                safe_p(a['created_by']),
            ])
        t_act = Table(act_rows, colWidths=[110, 50, 130, 160, 90])
        t_act.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_act)
    else:
        elements.append(Paragraph("No activity records found.", cell_style))

    # Section 5: Quotations
    elements.append(Paragraph(f"5. Quotations ({len(dossier['quotes'])} total)", h2_style))
    if dossier['quotes']:
        q_rows = [[
            Paragraph("Version", bold_cell_style),
            Paragraph("System kW", bold_cell_style),
            Paragraph("Brand", bold_cell_style),
            Paragraph("Gross Price", bold_cell_style),
            Paragraph("Tax / GST", bold_cell_style),
            Paragraph("Incentive", bold_cell_style),
            Paragraph("Status", bold_cell_style),
        ]]
        for q in dossier['quotes']:
            curr = q['currency']
            q_rows.append([
                safe_p(f"v{q['version']}"),
                safe_p(f"{q['system_size_kw']} kW"),
                safe_p(q['brand']),
                safe_p(f"{curr} {q['price']:,.2f}"),
                safe_p(f"{curr} {q['tax_amount']:,.2f}" if q['tax_amount'] else '-'),
                safe_p(f"{curr} {q['incentive_amount']:,.2f}"),
                safe_p(q['status']),
            ])
        t_q = Table(q_rows, colWidths=[45, 60, 95, 95, 85, 95, 65])
        t_q.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_q)
    else:
        elements.append(Paragraph("No quotation records found.", cell_style))

    # Section 6: Compliance Audit Trail
    elements.append(Paragraph(f"6. Compliance Audit Trail ({len(dossier['compliance_audit_logs'])} entries)", h2_style))
    if dossier['compliance_audit_logs']:
        audit_rows = [[
            Paragraph("Timestamp", bold_cell_style),
            Paragraph("Action", bold_cell_style),
            Paragraph("Actor", bold_cell_style),
            Paragraph("Reason / Justification", bold_cell_style),
        ]]
        for al in dossier['compliance_audit_logs'][:10]:
            audit_rows.append([
                safe_p(al['timestamp']),
                safe_p(al['action']),
                safe_p(al['user']),
                safe_p(al['reason'] or '-'),
            ])
        t_audit = Table(audit_rows, colWidths=[120, 110, 90, 220])
        t_audit.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf2f7')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_audit)

    # Footer note
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(
        "CONFIDENTIAL & PROPRIETARY. This dossier was generated automatically by Solar CRM compliance subsystem pursuant "
        "to applicable privacy and data protection regulations (e.g. DPDP Act 2023 in India, Privacy Act 1988 & APPs in Australia).",
        meta_style,
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def anonymize_lead_data(
    lead: Lead,
    reason: str,
    user: User,
    ip_address: Optional[str] = None,
) -> Lead:
    """
    Irreversibly anonymizes personal data of the lead for 'Right to be Forgotten' /
    data deletion requests. Preserves anonymous transaction and statistical history.
    """
    if not reason or len(reason.strip()) < 3:
        raise ValidationError("A specific reason of at least 3 characters is required to anonymize lead data.")

    # Record audit log BEFORE wiping
    AuditLog.objects.create(
        user=user,
        action='anonymize_lead',
        lead=lead,
        reason=reason.strip(),
        details={
            'previous_name': lead.name[:3] + '***',
            'lead_id': lead.id,
            'region': lead.region_id,
            'action_note': 'Personal identifiers permanently erased pursuant to privacy request.',
        },
        ip_address=ip_address,
    )

    lead.name = f"Anonymized Lead #{lead.id}"
    dummy_phone = "+910000000000" if lead.region_id == 'IN' else "+61000000000"
    lead.phone = dummy_phone
    lead.phone_e164 = dummy_phone
    lead.alt_phone = ""
    lead.alt_phone_e164 = ""
    lead.email = ""
    lead.address = "Redacted / Anonymized pursuant to Privacy Request"
    lead.city = ""
    lead.suburb = ""
    lead.pincode = ""
    lead.postcode = ""
    lead.consent_status = "withdrawn"
    lead.do_not_contact = True
    lead.save()

    return lead


def correct_lead_data(
    lead: Lead,
    updates: Dict[str, Any],
    reason: str,
    user: User,
    ip_address: Optional[str] = None,
) -> Lead:
    """
    Allows authorized administrators to rectify inaccurate personal information
    with a mandatory audit log entry and justification reason.
    """
    if not reason or len(reason.strip()) < 3:
        raise ValidationError("A specific reason is required to correct lead data.")

    allowed_fields = [
        'name', 'phone', 'alt_phone', 'email', 'address', 'city', 'suburb',
        'state', 'pincode', 'postcode', 'property_type', 'roof_type',
        'owner_or_tenant', 'bill_amount', 'bill_period', 'electricity_provider',
    ]

    applied_changes = {}
    region_code = lead.region_id or 'IN'

    for field, val in updates.items():
        if field not in allowed_fields:
            continue
        old_val = getattr(lead, field, None)

        if field == 'phone' and val:
            e164, _, err = normalize_phone_number(str(val), region_code)
            if err or not e164:
                raise ValidationError({'phone': err or 'Invalid phone number format.'})
            setattr(lead, 'phone', e164)
            setattr(lead, 'phone_e164', e164)
            applied_changes['phone'] = {'old': str(old_val), 'new': e164}
        elif field == 'alt_phone' and val:
            alt_e164, _, alt_err = normalize_phone_number(str(val), region_code)
            if alt_err or not alt_e164:
                raise ValidationError({'alt_phone': alt_err or 'Invalid alternate phone.'})
            setattr(lead, 'alt_phone', alt_e164)
            setattr(lead, 'alt_phone_e164', alt_e164)
            applied_changes['alt_phone'] = {'old': str(old_val), 'new': alt_e164}
        else:
            setattr(lead, field, val)
            applied_changes[field] = {'old': str(old_val), 'new': str(val)}

    if applied_changes:
        lead.save()
        AuditLog.objects.create(
            user=user,
            action='correct_lead_data',
            lead=lead,
            reason=reason.strip(),
            details={'changes': applied_changes},
            ip_address=ip_address,
        )

    return lead
