from django.core.management.base import BaseCommand

from messaging.models import MessageTemplate


class Command(BaseCommand):
    help = "Seeds default message templates for WhatsApp messaging."

    def handle(self, *args, **options):
        templates = [
            {
                'name': 'survey_confirmation',
                'description': 'Sent when a site survey is booked',
                'body': 'Namaste {customer_name}! Your solar site survey with Solar CRM has been confirmed for {time}. Our solar engineer will visit your property at {address}. Please ensure terrace roof access is accessible.',
            },
            {
                'name': 'survey_reminder',
                'description': 'Sent 1 day before the scheduled site survey at 18:00',
                'body': 'Namaste {customer_name}, this is a gentle reminder that your solar site survey is scheduled for tomorrow at {time}. Our engineer will inspect your roof space and electrical setup at {address}. See you tomorrow!',
            },
            {
                'name': 'brochure_and_savings',
                'description': 'Sent to interested leads wanting brochures and payback details',
                'body': 'Namaste {customer_name}! Thank you for your interest in rooftop solar. With our high-efficiency mono-PERC systems, you can save up to 80% on your monthly electricity bill with 4-5 year payback. Please review our brochure.',
            },
            {
                'name': 'quote_sent',
                'description': 'Sent when a customized solar quote is prepared and dispatched',
                'body': 'Namaste {customer_name}! Your customized solar proposal for a {system_size_kw} kW system ({brand}) amounting to ₹{price} is ready. We have factored in applicable PM Surya Ghar subsidies. Let us know when we can discuss!',
            },
        ]

        for item in templates:
            obj, created = MessageTemplate.objects.update_or_create(
                name=item['name'],
                defaults={
                    'description': item['description'],
                    'body': item['body'],
                    'is_active': True,
                }
            )
            action = "Created" if created else "Updated/Verified"
            self.stdout.write(f"  [{action}] Template: {obj.name}")

        self.stdout.write(self.style.SUCCESS("Message templates seeded successfully."))
