from decimal import Decimal
import phonenumbers
from django.db import migrations


def seed_and_migrate_forward(apps, schema_editor):
    Region = apps.get_model('masters', 'Region')
    State = apps.get_model('masters', 'State')
    RoofType = apps.get_model('masters', 'RoofType')
    PropertyType = apps.get_model('masters', 'PropertyType')
    User = apps.get_model('accounts', 'User')
    Lead = apps.get_model('leads', 'Lead')
    Quote = apps.get_model('quotes', 'Quote')
    MessageTemplate = apps.get_model('messaging', 'MessageTemplate')

    # 1. Seed Region IN
    region_in, _ = Region.objects.update_or_create(
        code='IN',
        defaults={
            'name': 'India',
            'currency': 'INR',
            'currency_symbol': '₹',
            'default_timezone': 'Asia/Kolkata',
            'phone_country_code': '+91',
            'locale': 'en-IN',
            'tax_label': 'GST',
            'tax_rate': Decimal('0.0500'),
            'incentive_label': 'Subsidy',
            'electricity_provider_label': 'DISCOM',
            'preferred_channels': ['whatsapp', 'sms'],
            'calling_hours_start': '09:00:00',
            'calling_hours_end_weekday': '20:00:00',
            'calling_hours_end_saturday': '20:00:00',
            'sunday_calling_allowed': True,
            'sunday_hours_start': '09:00:00',
            'sunday_hours_end': '20:00:00',
            'calling_hours_policy': 'warn',
            'dncr_validity_days': 30,
            'opt_out_text': 'Reply STOP to opt out',
            'privacy_notice_text': 'We process customer contact data strictly per Indian DPDP Act 2023 for rooftop solar system feasibility estimation.',
            'region_notes': 'PM Surya Ghar Muft Bijli Yojana provides central financial assistance of up to ₹78,000 direct bank transfer for residential solar systems up to 3 kW. DISCOM net metering connectivity regulations apply.',
            'is_active': True,
            'sort_order': 1,
        }
    )

    # 2. Seed Region AU
    region_au, _ = Region.objects.update_or_create(
        code='AU',
        defaults={
            'name': 'Australia',
            'currency': 'AUD',
            'currency_symbol': 'A$',
            'default_timezone': 'Australia/Sydney',
            'phone_country_code': '+61',
            'locale': 'en-AU',
            'tax_label': 'GST',
            'tax_rate': Decimal('0.1000'),
            'incentive_label': 'Government incentive (STCs and rebates)',
            'electricity_provider_label': 'Electricity retailer',
            'preferred_channels': ['sms', 'whatsapp'],
            'calling_hours_start': '09:00:00',
            'calling_hours_end_weekday': '20:00:00',
            'calling_hours_end_saturday': '17:00:00',
            'sunday_calling_allowed': False,
            'calling_hours_policy': 'warn',
            'dncr_validity_days': 30,
            'opt_out_text': 'Reply STOP to opt out',
            'privacy_notice_text': 'Your personal information is collected in accordance with the Australian Privacy Principles (APPs) under the Privacy Act 1988 for rooftop solar and battery feasibility inquiries.',
            'region_notes': 'Small-scale Technology Certificates (STCs) provide an upfront discount for eligible solar systems up to 100 kW. State-based battery incentives and feed-in tariffs vary by distribution network service provider (DNSP).',
            'is_active': True,
            'sort_order': 2,
        }
    )

    # 3. Seed Australian States & Territories
    au_states = [
        ('NSW', 'New South Wales', 'Australia/Sydney'),
        ('VIC', 'Victoria', 'Australia/Melbourne'),
        ('QLD', 'Queensland', 'Australia/Brisbane'),
        ('WA', 'Western Australia', 'Australia/Perth'),
        ('SA', 'South Australia', 'Australia/Adelaide'),
        ('TAS', 'Tasmania', 'Australia/Hobart'),
        ('ACT', 'Australian Capital Territory', 'Australia/Sydney'),
        ('NT', 'Northern Territory', 'Australia/Darwin'),
    ]
    for code, name, tz in au_states:
        State.objects.update_or_create(
            region=region_au,
            code=code,
            defaults={'name': name, 'default_timezone': tz, 'is_active': True}
        )

    # 4. Seed Indian States & UTs
    in_states = [
        ('AP', 'Andhra Pradesh'), ('AR', 'Arunachal Pradesh'), ('AS', 'Assam'),
        ('BR', 'Bihar'), ('CG', 'Chhattisgarh'), ('GA', 'Goa'), ('GJ', 'Gujarat'),
        ('HR', 'Haryana'), ('HP', 'Himachal Pradesh'), ('JH', 'Jharkhand'),
        ('KA', 'Karnataka'), ('KL', 'Kerala'), ('MP', 'Madhya Pradesh'),
        ('MH', 'Maharashtra'), ('MN', 'Manipur'), ('ML', 'Meghalaya'),
        ('MZ', 'Mizoram'), ('NL', 'Nagaland'), ('OD', 'Odisha'),
        ('PB', 'Punjab'), ('RJ', 'Rajasthan'), ('SK', 'Sikkim'),
        ('TN', 'Tamil Nadu'), ('TS', 'Telangana'), ('TR', 'Tripura'),
        ('UP', 'Uttar Pradesh'), ('UK', 'Uttarakhand'), ('WB', 'West Bengal'),
        ('AN', 'Andaman and Nicobar Islands'), ('CH', 'Chandigarh'),
        ('DN', 'Dadra and Nagar Haveli and Daman and Diu'), ('DL', 'Delhi'),
        ('JK', 'Jammu and Kashmir'), ('LA', 'Ladakh'), ('LD', 'Lakshadweep'),
        ('PY', 'Puducherry'),
    ]
    for code, name in in_states:
        State.objects.update_or_create(
            region=region_in,
            code=code,
            defaults={'name': name, 'default_timezone': 'Asia/Kolkata', 'is_active': True}
        )

    # 5. Seed Roof Types
    au_roofs = ['Concrete tile', 'Terracotta tile', 'Colorbond corrugated metal', 'Klip-lok metal', 'Flat concrete']
    for idx, r_name in enumerate(au_roofs):
        RoofType.objects.update_or_create(region=region_au, name=r_name, defaults={'sort_order': idx, 'is_active': True})

    in_roofs = ['RCC flat roof', 'Tin / Metal industrial sheet', 'Sloped Mangalore tile', 'Asbestos sheet']
    for idx, r_name in enumerate(in_roofs):
        RoofType.objects.update_or_create(region=region_in, name=r_name, defaults={'sort_order': idx, 'is_active': True})

    # 6. Seed Property Types
    au_props = ['Residential single-storey', 'Residential double-storey', 'Commercial premises', 'Rural / Farm property', 'Strata townhouse / unit']
    for idx, p_name in enumerate(au_props):
        PropertyType.objects.update_or_create(region=region_au, name=p_name, defaults={'sort_order': idx, 'is_active': True})

    in_props = ['Residential independent house', 'Residential villa', 'Commercial office / shop', 'Industrial shed / factory', 'Housing society common']
    for idx, p_name in enumerate(in_props):
        PropertyType.objects.update_or_create(region=region_in, name=p_name, defaults={'sort_order': idx, 'is_active': True})

    # 7. Migrate all existing users to Region IN and timezone Asia/Kolkata
    for user in User.objects.all():
        user.default_region = region_in
        user.default_timezone = 'Asia/Kolkata'
        user.save()
        user.allowed_regions.add(region_in)
        # Give Admin/Manager access to AU as well
        if user.role in ['admin', 'manager'] or user.is_superuser:
            user.allowed_regions.add(region_au)

    # 8. Migrate all existing leads to Region IN, timezone Asia/Kolkata, E.164 phone
    for lead in Lead.objects.all():
        lead.region = region_in
        lead.timezone = 'Asia/Kolkata'

        # Phone numbers: backup and E.164 normalization
        if not lead.phone_raw_backup:
            lead.phone_raw_backup = lead.phone
        if not lead.alt_phone_raw_backup:
            lead.alt_phone_raw_backup = lead.alt_phone or ''

        # Parse phone to E.164
        try:
            parsed = phonenumbers.parse(lead.phone, 'IN')
            if phonenumbers.is_valid_number(parsed):
                lead.phone_e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                lead.phone = lead.phone_e164
            else:
                clean = lead.phone.replace(' ', '').replace('-', '')
                lead.phone_e164 = f"+91{clean[-10:]}" if len(clean) >= 10 else f"+91{clean}"
        except Exception:
            clean = lead.phone.replace(' ', '').replace('-', '')
            lead.phone_e164 = f"+91{clean[-10:]}" if len(clean) >= 10 else f"+91{clean}"

        # Parse alt_phone
        if lead.alt_phone:
            try:
                parsed_alt = phonenumbers.parse(lead.alt_phone, 'IN')
                if phonenumbers.is_valid_number(parsed_alt):
                    lead.alt_phone_e164 = phonenumbers.format_number(parsed_alt, phonenumbers.PhoneNumberFormat.E164)
                    lead.alt_phone = lead.alt_phone_e164
                else:
                    clean_alt = lead.alt_phone.replace(' ', '').replace('-', '')
                    lead.alt_phone_e164 = f"+91{clean_alt[-10:]}" if len(clean_alt) >= 10 else f"+91{clean_alt}"
            except Exception:
                lead.alt_phone_e164 = ''

        # Electricity bill normalization
        if lead.monthly_bill is not None:
            lead.bill_amount = lead.monthly_bill
            lead.bill_period = 'monthly'
            lead.normalized_monthly_bill = lead.monthly_bill

        # Default consent
        if lead.consent_status == 'unknown':
            lead.consent_status = 'consented'
            lead.consent_source = 'Legacy lead database'

        lead.save()

    # 9. Migrate all existing quotes to Region IN
    for quote in Quote.objects.all():
        quote.region = region_in
        quote.currency = 'INR'
        quote.currency_symbol = '₹'
        quote.tax_included = True
        quote.tax_rate = Decimal('0.0500')
        if quote.price:
            p = Decimal(quote.price)
            quote.tax_amount = round(p - (p / Decimal('1.05')), 2)
        quote.incentive_label = 'Subsidy'
        quote.incentive_amount = quote.subsidy_amount or Decimal('0.00')
        quote.save()

    # 10. Update existing message templates with region_in
    for template in MessageTemplate.objects.filter(region__isnull=True):
        template.region = region_in
        template.channel = 'whatsapp'
        template.save()

    # Seed Australian SMS templates
    au_templates = [
        (
            'survey_confirmation',
            'sms',
            'Hi {customer_name}, your solar site inspection is booked for {time} at {address}. Our clean energy assessor will check roof space and switchboard. {opt_out_line}',
        ),
        (
            'survey_reminder',
            'sms',
            'Reminder: your solar site inspection is tomorrow at {time} at {address}. Please ensure clear roof and meter box access. {opt_out_line}',
        ),
        (
            'brochure_and_savings',
            'sms',
            'Hi {customer_name}, thanks for your rooftop solar inquiry! Learn how Australian STC rebates and solar can cut your electricity bills: {link}. {opt_out_line}',
        ),
        (
            'quote_sent',
            'sms',
            'Hi {customer_name}, your custom {system_size_kw} kW solar proposal ({brand}) for A${price} is ready to review. {opt_out_line}',
        ),
    ]
    for name, channel, body in au_templates:
        MessageTemplate.objects.update_or_create(
            region=region_au,
            name=name,
            channel=channel,
            defaults={'body': body, 'is_active': True}
        )


def seed_and_migrate_reverse(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Lead = apps.get_model('leads', 'Lead')
    Quote = apps.get_model('quotes', 'Quote')

    for lead in Lead.objects.all():
        if lead.phone_raw_backup:
            lead.phone = lead.phone_raw_backup
        if lead.alt_phone_raw_backup:
            lead.alt_phone = lead.alt_phone_raw_backup
        lead.phone_e164 = ''
        lead.alt_phone_e164 = ''
        lead.region = None
        lead.save()

    for quote in Quote.objects.all():
        quote.region = None
        quote.save()

    for user in User.objects.all():
        user.default_region = None
        user.allowed_regions.clear()
        user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0002_region_policysettings_data_retention_days_and_more'),
        ('accounts', '0002_user_allowed_regions_user_default_region_and_more'),
        ('quotes', '0003_quote_battery_kwh_quote_currency_and_more'),
        ('messaging', '0002_alter_messagetemplate_options_messagelog_channel_and_more'),
        ('leads', '0004_auditlog_lead_alt_phone_e164_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_and_migrate_forward, seed_and_migrate_reverse),
    ]
