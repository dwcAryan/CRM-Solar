import random
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from activities.models import Activity
from leads.models import Lead, LeadStatusHistory
from masters.models import LeadSource, LostReason, NurtureReason
from quotes.models import Quote
from surveys.models import Survey


class Command(BaseCommand):
    help = "Seeds demo users (admin, manager, salespeople, surveyor) and 30 realistic Indian sample leads with activities, surveys, and quotes."

    def handle(self, *args, **options):
        self.stdout.write("Ensuring master data is seeded...")
        call_command('seed_masters')

        self.stdout.write("\nCreating demo users...")
        users = self.seed_users()

        self.stdout.write("\nCreating 30 sample Indian leads...")
        self.seed_leads(users)

        self.stdout.write(self.style.SUCCESS("\nDemo data seeding completed successfully!"))
        self.print_user_credentials()

    def seed_users(self):
        user_specs = [
            {
                'username': 'demo_admin',
                'email': 'admin@solarcrm.com',
                'password': 'Admin@Demo2026!',
                'first_name': 'Amit',
                'last_name': 'Patel',
                'role': User.Role.ADMIN,
                'phone': '9825011111',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'demo_manager',
                'email': 'manager@solarcrm.com',
                'password': 'Manager@Demo2026!',
                'first_name': 'Vikram',
                'last_name': 'Shah',
                'role': User.Role.MANAGER,
                'phone': '9825022222',
                'is_staff': True,
                'is_superuser': False,
            },
            {
                'username': 'demo_sales1',
                'email': 'sales1@solarcrm.com',
                'password': 'Sales1@Demo2026!',
                'first_name': 'Rahul',
                'last_name': 'Desai',
                'role': User.Role.SALESPERSON,
                'phone': '9825033333',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': 'demo_sales2',
                'email': 'sales2@solarcrm.com',
                'password': 'Sales2@Demo2026!',
                'first_name': 'Pooja',
                'last_name': 'Mehta',
                'role': User.Role.SALESPERSON,
                'phone': '9825044444',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': 'demo_surveyor',
                'email': 'surveyor@solarcrm.com',
                'password': 'Surveyor@Demo2026!',
                'first_name': 'Sanjay',
                'last_name': 'Joshi',
                'role': User.Role.SURVEYOR,
                'phone': '9825055555',
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        created_users = {}
        for spec in user_specs:
            u, _ = User.objects.get_or_create(
                username=spec['username'],
                defaults={
                    'email': spec['email'],
                    'first_name': spec['first_name'],
                    'last_name': spec['last_name'],
                    'role': spec['role'],
                    'phone': spec['phone'],
                    'is_staff': spec['is_staff'],
                    'is_superuser': spec['is_superuser'],
                }
            )
            u.set_password(spec['password'])
            u.save()
            created_users[spec['username']] = u

        return created_users

    def print_user_credentials(self):
        self.stdout.write("=" * 60)
        self.stdout.write("DEMO USER CREDENTIALS FOR TESTING:")
        self.stdout.write("=" * 60)
        self.stdout.write("  Admin:       username: demo_admin     password: Admin@Demo2026!")
        self.stdout.write("  Manager:     username: demo_manager   password: Manager@Demo2026!")
        self.stdout.write("  Salesperson: username: demo_sales1    password: Sales1@Demo2026!")
        self.stdout.write("  Salesperson: username: demo_sales2    password: Sales2@Demo2026!")
        self.stdout.write("  Surveyor:    username: demo_surveyor  password: Surveyor@Demo2026!")
        self.stdout.write("=" * 60)

    def seed_leads(self, users):
        sales_pool = [users['demo_sales1'], users['demo_sales2']]
        surveyor = users['demo_surveyor']
        sources = list(LeadSource.objects.all())
        lost_reasons = list(LostReason.objects.all())
        nurture_reasons = list(NurtureReason.objects.all())

        lead_data_list = [
            ("Kavita Trivedi", "9898012345", "Ahmedabad", 3500, "Bungalow", "RCC Flat", Lead.Status.NEW),
            ("Harishchandra Dave", "9898023456", "Surat", 6200, "Row House", "RCC Flat", Lead.Status.ATTEMPTING_CONTACT),
            ("Nilesh Parikh", "9898034567", "Vadodara", 4800, "Villa", "Tin Shed", Lead.Status.ATTEMPTING_CONTACT),
            ("Bhavna Patel", "9898045678", "Rajkot", 8500, "Commercial Office", "RCC Flat", Lead.Status.CALLBACK_SCHEDULED),
            ("Chetan Solanki", "9898056789", "Ahmedabad", 5200, "Tenement", "Sloped Tile", Lead.Status.FOLLOW_UP),
            ("Dharmesh Bhatt", "9898067890", "Bhavnagar", 4100, "Bungalow", "RCC Flat", Lead.Status.INTERESTED),
            ("Falguni Vora", "9898078901", "Gandhinagar", 9000, "Independent House", "RCC Flat", Lead.Status.INTERESTED),
            ("Girish Shah", "9898089012", "Surat", 12500, "Industrial Shed", "Metal Sheet", Lead.Status.SURVEY_TO_SCHEDULE),
            ("Hasmukh Panchal", "9898090123", "Ahmedabad", 4500, "Row House", "RCC Flat", Lead.Status.SURVEY_SCHEDULED),
            ("Ila Merchant", "9898101234", "Vadodara", 3800, "Tenement", "RCC Flat", Lead.Status.SURVEY_SCHEDULED),
            ("Jagdish Soni", "9898112345", "Rajkot", 7200, "Bungalow", "RCC Flat", Lead.Status.SURVEY_RESCHEDULED),
            ("Kalpesh Prajapati", "9898123456", "Surat", 5600, "Villa", "RCC Flat", Lead.Status.SURVEY_MISSED),
            ("Lalitaben Modi", "9898134567", "Ahmedabad", 4300, "Bungalow", "RCC Flat", Lead.Status.DESIGN_PENDING),
            ("Mayur Chokshi", "9898145678", "Vadodara", 11000, "Commercial Complex", "RCC Flat", Lead.Status.DESIGN_PENDING),
            ("Nayan Kothari", "9898156789", "Jamnagar", 3200, "Tenement", "Asbestos", Lead.Status.ALTERNATIVE),
            ("Pravin Thakkar", "9898167890", "Surat", 6800, "Row House", "RCC Flat", Lead.Status.QUOTE_SENT),
            ("Rameshwar Joshi", "9898178901", "Ahmedabad", 5900, "Bungalow", "RCC Flat", Lead.Status.QUOTE_SENT),
            ("Sandip Makwana", "9898189012", "Rajkot", 8200, "Independent House", "RCC Flat", Lead.Status.REVISING_QUOTE),
            ("Tushar Sanghavi", "9898190123", "Surat", 14000, "Factory Shed", "Metal Sheet", Lead.Status.NEGOTIATION),
            ("Urmila Raval", "9898201234", "Ahmedabad", 5400, "Row House", "RCC Flat", Lead.Status.NEGOTIATION),
            ("Varun Gadhvi", "9898212345", "Vadodara", 7500, "Bungalow", "RCC Flat", Lead.Status.WON),
            ("Yogesh Sheth", "9898223456", "Surat", 9800, "Commercial Shop", "RCC Flat", Lead.Status.WON),
            ("Zahid Memon", "9898234567", "Ahmedabad", 16000, "Hospital Clinic", "RCC Flat", Lead.Status.WON),
            ("Anand Barot", "9898245678", "Rajkot", 3100, "Tenement", "Tin Shed", Lead.Status.LOST),
            ("Brijesh Shukla", "9898256789", "Bhavnagar", 4600, "Row House", "RCC Flat", Lead.Status.LOST),
            ("Chirag Dabhi", "9898267890", "Ahmedabad", 5100, "Bungalow", "RCC Flat", Lead.Status.LOST),
            ("Deepak Chaudhari", "9898278901", "Mehsana", 6300, "Farmhouse", "RCC Flat", Lead.Status.NURTURE),
            ("Elesh Parmar", "9898289012", "Anand", 4900, "Row House", "RCC Flat", Lead.Status.NURTURE),
            ("Gautam Rathod", "9898290123", "Ahmedabad", 2800, "Tenement", "RCC Flat", Lead.Status.UNREACHABLE),
            ("Hiren Kanzariya", "9898301234", "Surat", 4000, "Apartment (Rented)", "Common Terrace", Lead.Status.DO_NOT_CONTACT),
        ]

        now = timezone.now()

        for idx, (name, phone, city, bill, prop, roof, status_val) in enumerate(lead_data_list, start=1):
            assigned_rep = sales_pool[idx % len(sales_pool)]
            source_obj = sources[idx % len(sources)] if sources else None

            lost_res = lost_reasons[idx % len(lost_reasons)] if (status_val == Lead.Status.LOST and lost_reasons) else None
            nurture_res = nurture_reasons[idx % len(nurture_reasons)] if (status_val == Lead.Status.NURTURE and nurture_reasons) else None

            # Determine follow-up date
            if status_val in Lead.TERMINAL_STATUSES:
                followup_at = None
            elif idx % 4 == 0:
                # Overdue follow-up for dashboard testing
                followup_at = now - timedelta(days=random.randint(1, 5))
            elif idx % 4 == 1:
                # Due today
                followup_at = now + timedelta(hours=random.randint(1, 5))
            else:
                # Due in upcoming days
                followup_at = now + timedelta(days=random.randint(2, 7))

            won_time = (now - timedelta(days=random.randint(2, 20))) if status_val == Lead.Status.WON else None

            lead, created = Lead.objects.update_or_create(
                phone=phone,
                defaults={
                    'name': name,
                    'city': city,
                    'monthly_bill': bill,
                    'property_type': prop,
                    'roof_type': roof,
                    'owner_or_tenant': 'Owner' if 'Rented' not in prop else 'Tenant',
                    'source': source_obj,
                    'assigned_to': assigned_rep,
                    'status': status_val,
                    'next_action': f"Follow-up for {status_val}",
                    'next_followup_at': followup_at,
                    'lost_reason': lost_res,
                    'nurture_reason': nurture_res,
                    'do_not_contact': (status_val == Lead.Status.DO_NOT_CONTACT),
                    'attempt_count': 5 if status_val == Lead.Status.UNREACHABLE else (2 if status_val == Lead.Status.ATTEMPTING_CONTACT else 0),
                    'won_at': won_time,
                }
            )

            # Record initial status history
            LeadStatusHistory.objects.get_or_create(
                lead=lead,
                old_status=Lead.Status.NEW,
                new_status=status_val,
                defaults={
                    'changed_by': assigned_rep,
                    'note': f"Initial transition to {status_val} during onboarding",
                }
            )

            # Add activity
            Activity.objects.get_or_create(
                lead=lead,
                type=Activity.Type.CALL,
                status_after=status_val,
                defaults={
                    'next_action': lead.next_action,
                    'next_followup_at': lead.next_followup_at,
                    'notes': f"Demo activity record for {lead.name}",
                    'created_by': assigned_rep,
                }
            )

            # Add Survey if lead reached survey or beyond
            if status_val in [
                Lead.Status.SURVEY_SCHEDULED,
                Lead.Status.SURVEY_RESCHEDULED,
                Lead.Status.SURVEY_MISSED,
                Lead.Status.DESIGN_PENDING,
                Lead.Status.ALTERNATIVE,
                Lead.Status.QUOTE_SENT,
                Lead.Status.WON,
            ]:
                survey_status = Survey.Status.BOOKED
                if status_val == Lead.Status.SURVEY_RESCHEDULED:
                    survey_status = Survey.Status.RESCHEDULED
                elif status_val == Lead.Status.SURVEY_MISSED:
                    survey_status = Survey.Status.MISSED
                elif status_val in [Lead.Status.DESIGN_PENDING, Lead.Status.QUOTE_SENT, Lead.Status.WON]:
                    survey_status = Survey.Status.DONE

                Survey.objects.get_or_create(
                    lead=lead,
                    defaults={
                        'scheduled_at': now + timedelta(days=2),
                        'surveyor': surveyor,
                        'status': survey_status,
                        'site_suitable': True if survey_status == Survey.Status.DONE else None,
                        'notes': f"Site survey conducted for {lead.name}",
                    }
                )

            # Add Quote if lead reached quote sent, negotiation, or won
            if status_val in [Lead.Status.QUOTE_SENT, Lead.Status.REVISING_QUOTE, Lead.Status.NEGOTIATION, Lead.Status.WON]:
                quote_status = Quote.Status.SENT
                if status_val == Lead.Status.REVISING_QUOTE:
                    quote_status = Quote.Status.REVISED
                elif status_val == Lead.Status.WON:
                    quote_status = Quote.Status.ACCEPTED

                Quote.objects.get_or_create(
                    lead=lead,
                    version=1,
                    defaults={
                        'system_size_kw': 5.0,
                        'brand': 'Waaree 540W Mono PERC + Solis Inverter',
                        'price': 285000.00,
                        'subsidy_amount': 78000.00,
                        'status': quote_status,
                        'notes': f"Standard 5kW proposal for {lead.name}",
                        'created_by': assigned_rep,
                    }
                )

        self.stdout.write("  Created/Verified 30 leads across diverse statuses.")
