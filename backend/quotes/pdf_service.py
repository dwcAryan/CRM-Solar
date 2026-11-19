"""
Quotation PDF Generation Service (Phase 14M).
Generates standard A4 PDF quotations with:
- Line items, Solar specs, Inverter & Battery details
- Country-specific tax breakdown:
  * India: CGST & SGST (e.g. 2.5% + 2.5%)
  * Australia: GST (10%)
- Region incentive deductions (PM Surya Ghar Subsidy / STC Solar Rebate)
- Payment milestones & Bank details
- Customer acceptance & Company signature blocks
- Multi-currency formatting (₹, A$)
- Concurrency control (max 2 renders) with 15s timeout
"""
import html
import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config.pdf_engine import RenderSlotContext, ensure_unicode_fonts
from quotes.models import Quote


def format_currency_amount(amount: Any, symbol: str) -> str:
    if amount is None:
        return f"{symbol}0.00"
    try:
        val = float(amount)
        return f"{symbol}{val:,.2f}"
    except (ValueError, TypeError):
        return f"{symbol}{amount}"


def generate_quote_pdf(quote: Quote) -> bytes:
    """
    Renders an official quotation PDF for a given Quote instance.
    Returns raw PDF bytes.
    """
    regular_font, bold_font = ensure_unicode_fonts()

    lead = quote.lead
    region = quote.region or getattr(lead, 'region', None)
    region_code = getattr(region, 'code', 'IN') if region else 'IN'
    currency_symbol = quote.currency_symbol or (getattr(region, 'currency_symbol', '₹') if region else '₹')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'QuoteTitle',
        parent=styles['Heading1'],
        fontName=bold_font,
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        'QuoteSubtitle',
        parent=styles['Normal'],
        fontName=regular_font,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#4a5568'),
    )
    h2_style = ParagraphStyle(
        'QuoteSectionHeading',
        parent=styles['Heading2'],
        fontName=bold_font,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#2b6cb0'),
        spaceBefore=10,
        spaceAfter=4,
    )
    cell_style = ParagraphStyle(
        'QuoteTableCell',
        parent=styles['Normal'],
        fontName=regular_font,
        fontSize=8.5,
        leading=11,
    )
    bold_cell_style = ParagraphStyle(
        'QuoteTableBoldCell',
        parent=styles['Normal'],
        fontName=bold_font,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#2d3748'),
    )
    header_cell_style = ParagraphStyle(
        'QuoteHeaderCell',
        parent=styles['Normal'],
        fontName=bold_font,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#ffffff'),
    )

    def safe_p(text: Any, style=cell_style) -> Paragraph:
        val = "" if text is None else str(text)
        return Paragraph(html.escape(val), style)

    elements = []

    # 1. Header Banner & Branding
    elements.append(Paragraph("Solar CRM Quotation", title_style))
    quote_date = quote.created_at.strftime('%d/%m/%Y') if quote.created_at else 'Current'
    elements.append(Paragraph(
        f"<b>Quotation #:</b> Q-{quote.id:05d} (v{quote.version}) &nbsp;|&nbsp; "
        f"<b>Date:</b> {quote_date} &nbsp;|&nbsp; "
        f"<b>Validity:</b> 30 Days from issuance",
        subtitle_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2b6cb0'), spaceBefore=6, spaceAfter=8))

    # 2. Customer & Site Information
    elements.append(Paragraph("1. Customer & Installation Details", h2_style))
    lead_name = getattr(lead, 'name', 'N/A')
    lead_phone = getattr(lead, 'phone_e164', None) or getattr(lead, 'phone', 'N/A')
    lead_email = getattr(lead, 'email', 'N/A')
    lead_city = getattr(lead, 'city', '') or getattr(lead, 'suburb', '') or 'N/A'
    state_obj = getattr(lead, 'state', None)
    if hasattr(state_obj, 'name'):
        lead_state = state_obj.name
    elif isinstance(state_obj, str):
        lead_state = state_obj
    else:
        lead_state = 'N/A'
    lead_region = region.name if hasattr(region, 'name') else str(region or 'India')

    customer_data = [
        [Paragraph("Customer Name", bold_cell_style), safe_p(lead_name),
         Paragraph("Lead / Project #", bold_cell_style), safe_p(lead.id)],
        [Paragraph("Contact Phone", bold_cell_style), safe_p(lead_phone),
         Paragraph("Email Address", bold_cell_style), safe_p(lead_email)],
        [Paragraph("City / Suburb", bold_cell_style), safe_p(lead_city),
         Paragraph("State / Territory", bold_cell_style), safe_p(lead_state)],
        [Paragraph("Country / Region", bold_cell_style), safe_p(lead_region),
         Paragraph("Prepared By", bold_cell_style), safe_p(quote.created_by.username if quote.created_by else 'Solar Rep')],
    ]
    t_cust = Table(customer_data, colWidths=[120, 145, 120, 140])
    t_cust.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_cust)

    # 3. System Technical Specifications
    elements.append(Paragraph("2. Proposed Solar System Specifications", h2_style))
    system_size_str = f"{quote.system_size_kw} kW" if quote.system_size_kw else "N/A"
    battery_str = f"{quote.battery_kwh} kWh Lithium-ion Storage" if quote.battery_kwh else "Grid-Tied (No Battery)"

    specs_data = [
        [Paragraph("System Capacity", bold_cell_style), safe_p(system_size_str),
         Paragraph("Equipment / Modules", bold_cell_style), safe_p(quote.brand)],
        [Paragraph("Energy Storage", bold_cell_style), safe_p(battery_str),
         Paragraph("Grid Connection", bold_cell_style), safe_p("Single / Three Phase Net Metering")],
    ]
    t_specs = Table(specs_data, colWidths=[120, 145, 120, 140])
    t_specs.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_specs)

    # 4. Pricing & Tax Breakdown
    elements.append(Paragraph("3. Commercial Quotation & Tax Breakdown", h2_style))
    items_header = [
        Paragraph("Description", header_cell_style),
        Paragraph("Qty / Rating", header_cell_style),
        Paragraph("Rate", header_cell_style),
        Paragraph("Amount", header_cell_style),
    ]

    gross_price = float(quote.price or 0)
    tax_amt = float(quote.tax_amount or 0)
    incentive_amt = float(quote.incentive_amount or 0)

    rows = [items_header]
    rows.append([
        safe_p(f"Turnkey Solar PV Installation ({quote.brand})"),
        safe_p(system_size_str),
        safe_p(format_currency_amount(gross_price, currency_symbol)),
        safe_p(format_currency_amount(gross_price, currency_symbol)),
    ])

    if quote.battery_kwh:
        rows.append([
            safe_p(f"Battery Energy Storage System ({quote.battery_kwh} kWh)"),
            safe_p("1 Unit"),
            safe_p("Included"),
            safe_p("Included"),
        ])

    # Government Incentive Deduction
    if incentive_amt > 0:
        incentive_label = quote.incentive_label or ('PM Surya Ghar Subsidy' if region_code == 'IN' else 'STC Solar Rebate')
        rows.append([
            safe_p(f"Government Incentive: {incentive_label}"),
            safe_p("Deduction"),
            safe_p(f"-{format_currency_amount(incentive_amt, currency_symbol)}"),
            safe_p(f"-{format_currency_amount(incentive_amt, currency_symbol)}"),
        ])

    # Tax Breakdown based on Region
    if region_code == 'AU':
        rows.append([
            safe_p("Australia Goods & Services Tax: GST (10%)"),
            safe_p("10.0%"),
            safe_p(format_currency_amount(tax_amt, currency_symbol)),
            safe_p(format_currency_amount(tax_amt, currency_symbol)),
        ])
    elif region_code == 'IN':
        half_tax = round(tax_amt / 2.0, 2)
        rows.append([
            safe_p("Central GST (CGST - 2.5%)"),
            safe_p("2.5%"),
            safe_p(format_currency_amount(half_tax, currency_symbol)),
            safe_p(format_currency_amount(half_tax, currency_symbol)),
        ])
        rows.append([
            safe_p("State GST (SGST - 2.5%)"),
            safe_p("2.5%"),
            safe_p(format_currency_amount(half_tax, currency_symbol)),
            safe_p(format_currency_amount(half_tax, currency_symbol)),
        ])
    else:
        tax_pct = float(quote.tax_rate or 0) * 100
        rows.append([
            safe_p(f"Sales Tax ({tax_pct:.1f}%)"),
            safe_p(f"{tax_pct:.1f}%"),
            safe_p(format_currency_amount(tax_amt, currency_symbol)),
            safe_p(format_currency_amount(tax_amt, currency_symbol)),
        ])

    # Net Total
    net_payable = gross_price - incentive_amt if incentive_amt > 0 else gross_price
    rows.append([
        Paragraph("<b>Total Payable (Inclusive of Taxes & Net of Subsidies)</b>", bold_cell_style),
        Paragraph("", bold_cell_style),
        Paragraph("", bold_cell_style),
        Paragraph(f"<b>{format_currency_amount(net_payable, currency_symbol)}</b>", bold_cell_style),
    ])

    t_pricing = Table(rows, colWidths=[245, 80, 100, 100], repeatRows=1)
    t_pricing.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2b6cb0')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#edf2f7')),
    ]))
    elements.append(t_pricing)

    # 5. Payment Terms & Bank Details
    elements.append(Paragraph("4. Payment Terms & Bank Details", h2_style))
    terms_text = (
        "<b>Payment Terms:</b><br/>"
        "• <b>10% Advance:</b> Due upon quotation signing and agreement finalization.<br/>"
        "• <b>70% Progress:</b> Due prior to equipment dispatch & structure mounting.<br/>"
        "• <b>20% Completion:</b> Due upon successful testing, commissioning & grid synchronization."
    )
    elements.append(Paragraph(terms_text, cell_style))
    elements.append(Spacer(1, 4))

    if region_code == 'AU':
        bank_info = [
            [Paragraph("Bank Name", bold_cell_style), safe_p("Commonwealth Bank of Australia"),
             Paragraph("Account Name", bold_cell_style), safe_p("Solar CRM Australia Pty Ltd")],
            [Paragraph("BSB Number", bold_cell_style), safe_p("062-000"),
             Paragraph("Account Number", bold_cell_style), safe_p("1234 5678")],
        ]
    else:
        bank_info = [
            [Paragraph("Bank Name", bold_cell_style), safe_p("State Bank of India"),
             Paragraph("Account Name", bold_cell_style), safe_p("Solar CRM Solutions India Pvt Ltd")],
            [Paragraph("Account Number", bold_cell_style), safe_p("39482019482"),
             Paragraph("IFSC / Branch", bold_cell_style), safe_p("SBIN0001234 (Mumbai Main)")],
        ]
    t_bank = Table(bank_info, colWidths=[120, 145, 120, 140])
    t_bank.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_bank)

    # 6. Formal Signatures Block
    elements.append(Paragraph("5. Authorization & Acceptance", h2_style))
    sig_data = [
        [
            Paragraph("<b>For Solar CRM:</b><br/><br/><br/>____________________________________<br/>Authorized Signatory<br/>Solar Solutions Team", cell_style),
            Paragraph("<b>Customer Acceptance:</b><br/><br/><br/>____________________________________<br/>Customer Signature & Date<br/>Name: " + html.escape(str(lead_name)), cell_style),
        ]
    ]
    t_sig = Table(sig_data, colWidths=[260, 265])
    t_sig.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ffffff')),
    ]))
    elements.append(t_sig)

    # Build with concurrency limiting
    with RenderSlotContext(timeout=15.0):
        doc.build(elements)

    buffer.seek(0)
    return buffer.getvalue()
