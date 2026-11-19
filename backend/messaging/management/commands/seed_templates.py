from django.core.management.base import BaseCommand
from messaging.models import MessageTemplate


class Command(BaseCommand):
    help = "Seeds default message templates for WhatsApp messaging across languages."

    def handle(self, *args, **options):
        templates = [
            # English templates
            {
                'name': 'survey_confirmation',
                'language': 'en',
                'description': 'Sent when a site survey is booked',
                'body': 'Namaste {customer_name}! Your solar site survey with Solar CRM has been confirmed for {time}. Our solar engineer will visit your property at {address}. Please ensure terrace roof access is accessible. {opt_out_line}',
                'approval_status': 'approved',
            },
            {
                'name': 'survey_reminder',
                'language': 'en',
                'description': 'Sent 1 day before the scheduled site survey at 18:00',
                'body': 'Namaste {customer_name}, this is a gentle reminder that your solar site survey is scheduled for tomorrow at {time}. Our engineer will inspect your roof space and electrical setup at {address}. See you tomorrow! {opt_out_line}',
                'approval_status': 'approved',
            },
            {
                'name': 'brochure_and_savings',
                'language': 'en',
                'description': 'Sent to interested leads wanting brochures and payback details',
                'body': 'Namaste {customer_name}! Thank you for your interest in rooftop solar. With our high-efficiency mono-PERC systems, you can save up to 80% on your monthly electricity bill with 4-5 year payback. Please review our brochure. {opt_out_line}',
                'approval_status': 'approved',
            },
            {
                'name': 'quote_sent',
                'language': 'en',
                'description': 'Sent when a customized solar quote is prepared and dispatched',
                'body': 'Namaste {customer_name}! Your customized solar proposal for a {system_size_kw} kW system ({brand}) amounting to ₹{price} is ready. We have factored in applicable PM Surya Ghar subsidies. Let us know when we can discuss! {opt_out_line}',
                'approval_status': 'approved',
            },
            # Hindi templates
            {
                'name': 'survey_confirmation',
                'language': 'hi',
                'description': 'साइट सर्वे बुक होने पर भेजा जाने वाला संदेश',
                'body': 'नमस्ते {customer_name}! सोलर सीआरएम के साथ आपका सोलर साइट सर्वे {time} के लिए निर्धारित किया गया है। हमारे इंजीनियर {address} पर विजिट करेंगे। कृपया छत तक पहुंच सुनिश्चित करें। {opt_out_line}',
                'approval_status': 'approved',
            },
            {
                'name': 'survey_reminder',
                'language': 'hi',
                'description': 'निर्धारित सर्वे से 1 दिन पूर्व शाम को स्मरण पत्र',
                'body': 'नमस्ते {customer_name}, यह एक विनम्र स्मरण पत्र है कि आपका सोलर साइट सर्वे कल {time} पर निर्धारित है। हमारे इंजीनियर {address} पर छत और वायरिंग का निरीक्षण करेंगे। {opt_out_line}',
                'approval_status': 'approved',
            },
            {
                'name': 'brochure_and_savings',
                'language': 'hi',
                'description': 'ब्रोशर और बचत विवरण की जानकारी',
                'body': 'नमस्ते {customer_name}! रूफटॉप सोलर में रुचि लेने के लिए धन्यवाद। हमारी उच्च दक्षता प्रणालियों के साथ आप अपने मासिक बिजली बिल पर 80% तक की बचत कर सकते हैं। अधिक जानकारी के लिए विवरण देखें। {opt_out_line}',
                'approval_status': 'approved',
            },
            {
                'name': 'quote_sent',
                'language': 'hi',
                'description': 'कोटेशन व प्रस्ताव तैयार होने पर संदेश',
                'body': 'नमस्ते {customer_name}! आपका {system_size_kw} किलोवाट सोलर प्रस्ताव ({brand}) कुल ₹{price} में तैयार है। इसमें सरकारी सब्सिडी शामिल है। चर्चा के लिए उपयुक्त समय बताएं! {opt_out_line}',
                'approval_status': 'approved',
            },
        ]

        for item in templates:
            obj, created = MessageTemplate.objects.update_or_create(
                name=item['name'],
                language=item['language'],
                region=None,
                channel=MessageTemplate.Channel.WHATSAPP,
                defaults={
                    'description': item['description'],
                    'body': item['body'],
                    'approval_status': item['approval_status'],
                    'is_active': True,
                }
            )
            action = "Created" if created else "Updated/Verified"
            self.stdout.write(f"  [{action}] Template [{item['language']}]: {obj.name}")

        self.stdout.write(self.style.SUCCESS("Message templates seeded successfully across languages."))
