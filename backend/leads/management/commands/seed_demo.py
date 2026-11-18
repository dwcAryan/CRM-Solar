from decimal import Decimal
import random
import secrets
import string
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from activities.models import Activity
from leads.models import Lead, LeadStatusHistory
from masters.models import LeadSource, LostReason, NurtureReason, Region, State
from quotes.models import Quote
from surveys.models import Survey


def generate_strong_password(length=14):
    """Generate a random strong password with lowercase, uppercase, digits, and symbols."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in pwd)
                and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in "!@#$%^&*" for c in pwd)):
            return pwd


class Command(BaseCommand):
    help = "Seeds demo users (multi-country) and 30 realistic sample leads (15 India, 15 Australia) with activities, surveys, and quotes."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing leads and re-seed all demo accounts and leads from scratch.',
        )

    def handle(self, *args, **options):
        if options.get('reset'):
            self.stdout.write(self.style.WARNING("Reset requested: deleting existing leads, quotes, surveys and activities..."))
            Quote.objects.all().delete()
            Survey.objects.all().delete()
            Activity.objects.all().delete()
            LeadStatusHistory.objects.all().delete()
            Lead.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Existing data cleared."))

        self.stdout.write("Ensuring master data is seeded...")
        call_command('seed_masters')

        self.stdout.write("\nCreating/updating demo users with randomized strong passwords...")
        users, credentials_info = self.seed_users()

        self.stdout.write("\nWriting generated credentials to docs/DEMO_ACCOUNTS.md...")
        self.write_demo_accounts_doc(credentials_info)

        self.stdout.write("\nCreating 15 Indian and 15 Australian sample leads...")
        self.seed_leads(users)

        self.stdout.write(self.style.SUCCESS("\nDemo data seeding completed successfully!"))
        self.print_user_credentials(credentials_info)

    def seed_users(self):
        in_region = Region.objects.get(code='IN')
        au_region = Region.objects.get(code='AU')

        user_specs = [
            {
                'username': 'demo_admin',
                'email': 'admin@solarcrm.com',
                'first_name': 'Amit',
                'last_name': 'Patel',
                'role': User.Role.ADMIN,
                'role_label': 'Admin',
                'phone': '+919825011111',
                'is_staff': True,
                'is_superuser': True,
                'default_region': in_region,
                'default_timezone': 'Asia/Kolkata',
                'allowed_regions': [in_region, au_region],
                'description': 'Full access, RBAC governance, master data, user management, audit logs',
            },
            {
                'username': 'demo_manager',
                'email': 'manager@solarcrm.com',
                'first_name': 'Vikram',
                'last_name': 'Shah',
                'role': User.Role.MANAGER,
                'role_label': 'Manager',
                'phone': '+919825022222',
                'is_staff': True,
                'is_superuser': False,
                'default_region': in_region,
                'default_timezone': 'Asia/Kolkata',
                'allowed_regions': [in_region, au_region],
                'description': 'Regional oversight, Manager Attention Queue, lead distribution, lost deal approvals',
            },
            {
                'username': 'demo_sales_in',
                'email': 'sales_in@solarcrm.com',
                'first_name': 'Rahul',
                'last_name': 'Desai',
                'role': User.Role.SALESPERSON,
                'role_label': 'Salesperson (IN)',
                'phone': '+919825033333',
                'is_staff': False,
                'is_superuser': False,
                'default_region': in_region,
                'default_timezone': 'Asia/Kolkata',
                'allowed_regions': [in_region],
                'description': 'India sales pipeline, log outcomes, book surveys, create quotes',
            },
            {
                'username': 'demo_sales_au',
                'email': 'sales_au@solarcrm.com',
                'first_name': 'Liam',
                'last_name': 'O\'Connor',
                'role': User.Role.SALESPERSON,
                'role_label': 'Salesperson (AU)',
                'phone': '+61412333333',
                'is_staff': False,
                'is_superuser': False,
                'default_region': au_region,
                'default_timezone': 'Australia/Sydney',
                'allowed_regions': [au_region],
                'description': 'Australia sales pipeline, DNCR consent checks, quarterly bills, STC quotes',
            },
            {
                'username': 'demo_surveyor_in',
                'email': 'surveyor_in@solarcrm.com',
                'first_name': 'Sanjay',
                'last_name': 'Joshi',
                'role': User.Role.SURVEYOR,
                'role_label': 'Surveyor (IN)',
                'phone': '+919825055555',
                'is_staff': False,
                'is_superuser': False,
                'default_region': in_region,
                'default_timezone': 'Asia/Kolkata',
                'allowed_regions': [in_region],
                'description': 'India site surveyor portal, technical feasibility, site photo upload',
            },
            {
                'username': 'demo_surveyor_au',
                'email': 'surveyor_au@solarcrm.com',
                'first_name': 'Jack',
                'last_name': 'Thompson',
                'role': User.Role.SURVEYOR,
                'role_label': 'Surveyor (AU)',
                'phone': '+61412555555',
                'is_staff': False,
                'is_superuser': False,
                'default_region': au_region,
                'default_timezone': 'Australia/Sydney',
                'allowed_regions': [au_region],
                'description': 'Australia site surveyor portal, switchboard and solar feasibility, site photos',
            },
        ]

        created_users = {}
        credentials_info = []

        for spec in user_specs:
            password = generate_strong_password()
            u, created = User.objects.get_or_create(
                username=spec['username'],
                defaults={
                    'email': spec['email'],
                    'first_name': spec['first_name'],
                    'last_name': spec['last_name'],
                    'role': spec['role'],
                    'phone': spec['phone'],
                    'is_staff': spec['is_staff'],
                    'is_superuser': spec['is_superuser'],
                    'default_region': spec['default_region'],
                    'default_timezone': spec['default_timezone'],
                }
            )
            u.set_password(password)
            u.save()
            u.allowed_regions.set(spec['allowed_regions'])
            created_users[spec['username']] = u

            regions_str = ", ".join([r.code for r in spec['allowed_regions']])
            credentials_info.append({
                'role_label': spec['role_label'],
                'username': spec['username'],
                'password': password,
                'regions': regions_str,
                'timezone': spec['default_timezone'],
                'phone': spec['phone'],
                'description': spec['description'],
            })
            self.stdout.write(f"  {'Created' if created else 'Updated'} user: {spec['username']} ({spec['role']})")

        return created_users, credentials_info

    def write_demo_accounts_doc(self, credentials_info):
        project_root = Path(settings.BASE_DIR).parent
        docs_dir = project_root / 'docs'
        docs_dir.mkdir(parents=True, exist_ok=True)
        doc_file = docs_dir / 'DEMO_ACCOUNTS.md'

        table_rows = []
        for cred in credentials_info:
            row = (
                f"| **{cred['role_label']}** "
                f"| `{cred['username']}` "
                f"| `{cred['password']}` "
                f"| {cred['regions']} "
                f"| `{cred['timezone']}` "
                f"| `{cred['phone']}` "
                f"| {cred['description']} |"
            )
            table_rows.append(row)

        content = f"""# Solar CRM - Demo Accounts & Access Credentials

> **CONFIDENTIAL - DEMO ENVIRONMENT ONLY**
> This file is generated dynamically by `python manage.py seed_demo`.
> It is excluded from version control (`.gitignore`). Passwords are randomly generated on each seed run.

## Active Demo Credentials

| Role | Username | Password | Regions | Timezone | Phone | Work Area & Responsibilities |
|:---|:---|:---|:---|:---|:---|:---|
{chr(10).join(table_rows)}

## Regional Defaults
- **India (IN)**: Currency INR (₹), Default Tax GST (5% solar equipment), DISCOM grid regulations.
- **Australia (AU)**: Currency AUD ($), Default Tax GST (10% inclusive), Clean Energy Council (CEC) STCs and battery subsidies.

## Quick Login Instructions
1. Open the Solar CRM frontend at [http://localhost:5173](http://localhost:5173).
2. Copy any username and password from the table above.
3. Log in to explore the role-specific workspace and dashboard for that user.
"""
        doc_file.write_text(content, encoding='utf-8')
        self.stdout.write(f"  Saved demo accounts file to {doc_file}")

    def print_user_credentials(self, credentials_info):
        self.stdout.write("\n" + "=" * 68)
        self.stdout.write("DEMO USER CREDENTIALS GENERATED")
        self.stdout.write("=" * 68)
        self.stdout.write("Passwords have been securely generated and saved to:")
        self.stdout.write("  --> docs/DEMO_ACCOUNTS.md (git-ignored)")
        self.stdout.write("\nDemo users ready:")
        for cred in credentials_info:
            self.stdout.write(f"  - {cred['username']:<18} ({cred['role_label']})")
        self.stdout.write("=" * 68 + "\n")

    def seed_leads(self, users):
        now = timezone.now()
        in_region = Region.objects.get(code='IN')
        au_region = Region.objects.get(code='AU')

        sales_in = users['demo_sales_in']
        sales_au = users['demo_sales_au']
        surveyor_in = users['demo_surveyor_in']
        surveyor_au = users['demo_surveyor_au']

        sources = list(LeadSource.objects.filter(is_active=True))
        default_source = sources[0] if sources else LeadSource.objects.create(name='Direct Referral')

        lost_res = LostReason.objects.filter(is_active=True).first()
        nurture_res = NurtureReason.objects.filter(is_active=True).first()

        # 15 Realistic Indian Leads
        indian_leads_data = [
            ("Rajesh Varma", "+919825110001", "Ahmedabad", "Gujarat", "Bodakdev", "380054", Lead.Status.NEW, 4500, "RCC flat"),
            ("Priya Patel", "+919825110002", "Surat", "Gujarat", "Vesu", "395007", Lead.Status.ATTEMPTING_CONTACT, 6200, "RCC flat"),
            ("Sunil Sharma", "+919825110003", "Vadodara", "Gujarat", "Alkapuri", "390007", Lead.Status.CALLBACK_SCHEDULED, 3800, "tin shade"),
            ("Ananya Desai", "+919825110004", "Rajkot", "Gujarat", "Kalawad Road", "360005", Lead.Status.INTERESTED, 8500, "RCC flat"),
            ("Deepak Mehta", "+919825110005", "Gandhinagar", "Gujarat", "Sector 8", "382008", Lead.Status.SURVEY_TO_SCHEDULE, 5400, "RCC flat"),
            ("Kavita Joshi", "+919825110006", "Mumbai", "Maharashtra", "Andheri West", "400058", Lead.Status.SURVEY_SCHEDULED, 9500, "RCC flat"),
            ("Manish Shah", "+919825110007", "Pune", "Maharashtra", "Baner", "411045", Lead.Status.DESIGN_PENDING, 7200, "tiled"),
            ("Suresh Trivedi", "+919825110008", "Ahmedabad", "Gujarat", "Satellite", "380015", Lead.Status.QUOTE_SENT, 12000, "RCC flat"),
            ("Bhavna Rao", "+919825110009", "Bangalore", "Karnataka", "Indiranagar", "560038", Lead.Status.NEGOTIATION, 6800, "RCC flat"),
            ("Nitin Kothari", "+919825110010", "Jaipur", "Rajasthan", "Malviya Nagar", "302017", Lead.Status.WON, 11500, "RCC flat"),
            ("Alok Gupta", "+919825110011", "Delhi", "Delhi", "Rohini Sector 9", "110085", Lead.Status.LOST, 3200, "RCC flat"),
            ("Meera Nambiar", "+919825110012", "Cochin", "Kerala", "Kakkanad", "682030", Lead.Status.NURTURE, 4100, "slanted tile"),
            ("Harish Reddy", "+919825110013", "Hyderabad", "Telangana", "Madhapur", "500081", Lead.Status.UNREACHABLE, 5800, "RCC flat"),
            ("Gaurav Kapoor", "+919825110014", "Chandigarh", "Punjab", "Sector 17", "160017", Lead.Status.DO_NOT_CONTACT, 2900, "RCC flat"),
            ("Neha Choudhary", "+919825110015", "Indore", "Madhya Pradesh", "Vijay Nagar", "452010", Lead.Status.FOLLOW_UP, 4700, "RCC flat"),
        ]

        # 15 Realistic Australian Leads
        australian_leads_data = [
            ("Lachlan Campbell", "+61412000001", "Sydney", "NSW", "Parramatta", "2150", Lead.Status.NEW, 850, "Colorbond", "quarterly", "Origin Energy", "Australia/Sydney"),
            ("Emma Watson", "+61412000002", "Melbourne", "VIC", "Richmond", "3121", Lead.Status.ATTEMPTING_CONTACT, 720, "Tile", "quarterly", "AGL", "Australia/Melbourne"),
            ("Jack Robinson", "+61412000003", "Brisbane", "QLD", "Chermside", "4032", Lead.Status.CALLBACK_SCHEDULED, 920, "Tin", "quarterly", "EnergyAustralia", "Australia/Brisbane"),
            ("Olivia Taylor", "+61412000004", "Perth", "WA", "Fremantle", "6160", Lead.Status.INTERESTED, 650, "Colorbond", "two_monthly", "Synergy", "Australia/Perth"),
            ("Noah Anderson", "+61412000005", "Adelaide", "SA", "Glenelg", "5045", Lead.Status.SURVEY_TO_SCHEDULE, 880, "Tile", "quarterly", "Red Energy", "Australia/Adelaide"),
            ("Charlotte Davies", "+61412000006", "Sydney", "NSW", "Cronulla", "2230", Lead.Status.SURVEY_SCHEDULED, 1100, "Colorbond", "quarterly", "Origin Energy", "Australia/Sydney"),
            ("Ethan Wright", "+61412000007", "Melbourne", "VIC", "Brunswick", "3056", Lead.Status.DESIGN_PENDING, 780, "Slate", "quarterly", "AGL", "Australia/Melbourne"),
            ("Mia Thomas", "+61412000008", "Brisbane", "QLD", "Paddington", "4064", Lead.Status.QUOTE_SENT, 950, "Tin", "quarterly", "Alinta Energy", "Australia/Brisbane"),
            ("Lucas Mitchell", "+61412000009", "Hobart", "TAS", "Sandy Bay", "7005", Lead.Status.NEGOTIATION, 1250, "Colorbond", "quarterly", "Aurora Energy", "Australia/Hobart"),
            ("Sophie Wilson", "+61412000010", "Canberra", "ACT", "Belconnen", "2617", Lead.Status.WON, 900, "Colorbond", "quarterly", "ActewAGL", "Australia/Sydney"),
            ("Benjamin Hall", "+61412000011", "Darwin", "NT", "Casuarina", "0810", Lead.Status.LOST, 1400, "Colorbond", "monthly", "Jacana Energy", "Australia/Darwin"),
            ("Amelia Evans", "+61412000012", "Gold Coast", "QLD", "Robina", "4226", Lead.Status.NURTURE, 760, "Tile", "quarterly", "Origin Energy", "Australia/Brisbane"),
            ("Henry Martin", "+61412000013", "Perth", "WA", "Joondalup", "6027", Lead.Status.UNREACHABLE, 600, "Colorbond", "two_monthly", "Synergy", "Australia/Perth"),
            ("Grace Clarke", "+61412000014", "Sydney", "NSW", "Manly", "2095", Lead.Status.DO_NOT_CONTACT, 980, "Tile", "quarterly", "EnergyAustralia", "Australia/Sydney"),
            ("William King", "+61412000015", "Melbourne", "VIC", "St Kilda", "3182", Lead.Status.FOLLOW_UP, 820, "Colorbond", "quarterly", "AGL", "Australia/Melbourne"),
        ]

        # Seed Indian Leads
        for name, phone, city, state, suburb, pin, status_val, bill, roof in indian_leads_data:
            followup = now + timedelta(days=random.randint(1, 5))
            won_time = now - timedelta(days=2) if status_val == Lead.Status.WON else None

            lead, created = Lead.objects.get_or_create(
                phone_e164=phone,
                defaults={
                    'name': name,
                    'phone': phone,
                    'phone_raw_backup': phone,
                    'email': f"{name.lower().replace(' ', '.')}@example.in",
                    'region': in_region,
                    'state': state,
                    'city': city,
                    'suburb': suburb,
                    'pincode': pin,
                    'address': f"{random.randint(1, 100)}, {suburb}, {city}",
                    'source': default_source,
                    'property_type': 'residential',
                    'monthly_bill': bill,
                    'bill_amount': Decimal(str(bill)),
                    'bill_period': 'monthly',
                    'normalized_monthly_bill': Decimal(str(bill)),
                    'electricity_provider': 'UGVCL / State DISCOM',
                    'roof_type': roof,
                    'owner_or_tenant': 'owner',
                    'assigned_to': sales_in,
                    'timezone': 'Asia/Kolkata',
                    'status': status_val,
                    'next_action': 'Follow up on solar quotation' if status_val == Lead.Status.QUOTE_SENT else 'Conduct phone consultation',
                    'next_followup_at': followup if status_val not in Lead.TERMINAL_STATUSES else None,
                    'lost_reason': lost_res if status_val == Lead.Status.LOST else None,
                    'nurture_reason': nurture_res if status_val == Lead.Status.NURTURE else None,
                    'do_not_contact': (status_val == Lead.Status.DO_NOT_CONTACT),
                    'consent_status': 'consented',
                    'consent_source': 'Online Enquiry Form',
                    'consent_date': now,
                    'attempt_count': 5 if status_val == Lead.Status.UNREACHABLE else (2 if status_val == Lead.Status.ATTEMPTING_CONTACT else 0),
                    'won_at': won_time,
                }
            )

            # Record Status History
            LeadStatusHistory.objects.get_or_create(
                lead=lead,
                old_status=Lead.Status.NEW,
                new_status=status_val,
                defaults={'changed_by': sales_in, 'note': f"Initial transition to {status_val}"}
            )

            # Record Activity
            Activity.objects.get_or_create(
                lead=lead,
                type=Activity.Type.CALL,
                status_after=status_val,
                defaults={
                    'next_action': lead.next_action,
                    'next_followup_at': lead.next_followup_at,
                    'notes': f"Sales discussion conducted with {lead.name}",
                    'created_by': sales_in,
                }
            )

            # Add Survey if applicable
            if status_val in [Lead.Status.SURVEY_SCHEDULED, Lead.Status.DESIGN_PENDING, Lead.Status.QUOTE_SENT, Lead.Status.WON]:
                Survey.objects.get_or_create(
                    lead=lead,
                    defaults={
                        'scheduled_at': now + timedelta(days=2),
                        'surveyor': surveyor_in,
                        'status': Survey.Status.DONE if status_val != Lead.Status.SURVEY_SCHEDULED else Survey.Status.BOOKED,
                        'site_suitable': True if status_val != Lead.Status.SURVEY_SCHEDULED else None,
                        'notes': f"Rooftop feasibility confirmed for {lead.name}",
                    }
                )

            # Add Quote if applicable
            if status_val in [Lead.Status.QUOTE_SENT, Lead.Status.NEGOTIATION, Lead.Status.WON]:
                Quote.objects.get_or_create(
                    lead=lead,
                    version=1,
                    defaults={
                        'region': in_region,
                        'currency': 'INR',
                        'currency_symbol': '₹',
                        'system_size_kw': Decimal('5.0'),
                        'brand': 'Waaree 540W Mono PERC + Solis Inverter',
                        'price': Decimal('285000.00'),
                        'tax_rate': Decimal('0.05'),
                        'tax_amount': Decimal('14250.00'),
                        'incentive_label': 'Subsidy (PM Surya Ghar)',
                        'incentive_amount': Decimal('78000.00'),
                        'subsidy_amount': Decimal('78000.00'),
                        'status': Quote.Status.ACCEPTED if status_val == Lead.Status.WON else Quote.Status.SENT,
                        'notes': f"Proposal v1 for {lead.name}",
                        'created_by': sales_in,
                    }
                )

        # Seed Australian Leads
        for name, phone, city, state, suburb, postc, status_val, bill_raw, roof, b_period, retailer, tz in australian_leads_data:
            followup = now + timedelta(days=random.randint(1, 5))
            won_time = now - timedelta(days=2) if status_val == Lead.Status.WON else None

            # Calculate normalized bill
            b_dec = Decimal(str(bill_raw))
            if b_period == 'quarterly':
                norm_bill = b_dec / Decimal(3)
            elif b_period == 'two_monthly':
                norm_bill = b_dec / Decimal(2)
            else:
                norm_bill = b_dec

            clean_email_name = name.lower().replace(' ', '.').replace("'", "")
            lead, created = Lead.objects.get_or_create(
                phone_e164=phone,
                defaults={
                    'name': name,
                    'phone': phone,
                    'phone_raw_backup': phone,
                    'email': f"{clean_email_name}@example.com.au",
                    'region': au_region,
                    'state': state,
                    'city': city,
                    'suburb': suburb,
                    'postcode': postc,
                    'pincode': postc,
                    'address': f"{random.randint(1, 99)} {suburb} Road",
                    'source': default_source,
                    'property_type': 'residential',
                    'monthly_bill': int(norm_bill),
                    'bill_amount': b_dec,
                    'bill_period': b_period,
                    'normalized_monthly_bill': norm_bill,
                    'electricity_provider': retailer,
                    'roof_type': roof,
                    'owner_or_tenant': 'owner',
                    'assigned_to': sales_au,
                    'timezone': tz,
                    'status': status_val,
                    'next_action': 'Review solar proposal and STC discount' if status_val == Lead.Status.QUOTE_SENT else 'Initial consultation via phone/SMS',
                    'next_followup_at': followup if status_val not in Lead.TERMINAL_STATUSES else None,
                    'lost_reason': lost_res if status_val == Lead.Status.LOST else None,
                    'nurture_reason': nurture_res if status_val == Lead.Status.NURTURE else None,
                    'do_not_contact': (status_val == Lead.Status.DO_NOT_CONTACT),
                    'consent_status': 'consented',
                    'consent_source': 'Solar Calculator AU',
                    'consent_date': now,
                    'dncr_status': 'not_on_register',
                    'dncr_checked_at': now,
                    'dncr_checked_by': sales_au,
                    'attempt_count': 5 if status_val == Lead.Status.UNREACHABLE else (2 if status_val == Lead.Status.ATTEMPTING_CONTACT else 0),
                    'won_at': won_time,
                }
            )

            # Record Status History
            LeadStatusHistory.objects.get_or_create(
                lead=lead,
                old_status=Lead.Status.NEW,
                new_status=status_val,
                defaults={'changed_by': sales_au, 'note': f"Lead placed in {status_val}"}
            )

            # Record Activity
            Activity.objects.get_or_create(
                lead=lead,
                type=Activity.Type.CALL,
                status_after=status_val,
                defaults={
                    'next_action': lead.next_action,
                    'next_followup_at': lead.next_followup_at,
                    'notes': f"Consultative discussion with {lead.name}",
                    'created_by': sales_au,
                }
            )

            # Add Survey if applicable
            if status_val in [Lead.Status.SURVEY_SCHEDULED, Lead.Status.DESIGN_PENDING, Lead.Status.QUOTE_SENT, Lead.Status.WON]:
                Survey.objects.get_or_create(
                    lead=lead,
                    defaults={
                        'scheduled_at': now + timedelta(days=2),
                        'surveyor': surveyor_au,
                        'status': Survey.Status.DONE if status_val != Lead.Status.SURVEY_SCHEDULED else Survey.Status.BOOKED,
                        'site_suitable': True if status_val != Lead.Status.SURVEY_SCHEDULED else None,
                        'notes': f"Switchboard and {roof} roof inspection completed for {lead.name}",
                    }
                )

            # Add Quote if applicable
            if status_val in [Lead.Status.QUOTE_SENT, Lead.Status.NEGOTIATION, Lead.Status.WON]:
                Quote.objects.get_or_create(
                    lead=lead,
                    version=1,
                    defaults={
                        'region': au_region,
                        'currency': 'AUD',
                        'currency_symbol': 'A$',
                        'system_size_kw': Decimal('6.6'),
                        'brand': 'Trina Vertex S+ 440W + Fronius Primo 5.0-1',
                        'price': Decimal('7800.00'),
                        'tax_rate': Decimal('0.10'),
                        'tax_amount': Decimal('709.09'),
                        'tax_included': True,
                        'incentive_label': 'Government incentive (STCs and rebates)',
                        'incentive_amount': Decimal('2640.00'),
                        'subsidy_amount': Decimal('2640.00'),
                        'battery_kwh': Decimal('9.6') if status_val == Lead.Status.WON else None,
                        'status': Quote.Status.ACCEPTED if status_val == Lead.Status.WON else Quote.Status.SENT,
                        'notes': f"Australian CEC-compliant 6.6kW proposal for {lead.name}",
                        'created_by': sales_au,
                    }
                )

        self.stdout.write("  Created/Verified 30 leads (15 IN, 15 AU) across diverse statuses.")
