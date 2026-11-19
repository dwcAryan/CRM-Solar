from django.core.management.base import BaseCommand
from django.db import transaction

from masters.models import (
    Language,
    LeadSource,
    LostReason,
    NurtureReason,
    Outcome,
    PolicySettings,
    PropertyType,
    Region,
    RoofType,
    State,
    TranslationEntry,
)


class Command(BaseCommand):
    help = "Seeds master data (Languages, Outcomes, LostReasons, NurtureReasons, LeadSources, PolicySettings, Translations) idempotently."

    def handle(self, *args, **options):
        self.stdout.write("Seeding master tables...")

        with transaction.atomic():
            self.seed_languages()
            self.seed_policy_settings()
            self.seed_lost_reasons()
            self.seed_nurture_reasons()
            self.seed_lead_sources()
            self.seed_outcomes()
            self.seed_regions_translations()
            self.seed_roof_and_property_types()
            self.seed_initial_translation_entries()

        self.stdout.write(self.style.SUCCESS("Master data seeded successfully and idempotently."))

    def seed_languages(self):
        languages = [
            {
                'code': 'en',
                'name': 'English',
                'native_name': 'English',
                'direction': 'ltr',
                'numbering_system': 'latn',
                'week_start': 1,
                'font_family_key': 'sans',
                'completeness_pct': 100.0,
                'review_status': 'reviewed',
                'sort_order': 1,
            },
            {
                'code': 'hi',
                'name': 'Hindi',
                'native_name': 'हिन्दी',
                'direction': 'ltr',
                'numbering_system': 'latn',
                'week_start': 1,
                'font_family_key': 'noto-sans-devanagari',
                'completeness_pct': 100.0,
                'review_status': 'reviewed',
                'sort_order': 2,
            },
            {
                'code': 'en-AU',
                'name': 'English (Australia)',
                'native_name': 'English (AU)',
                'direction': 'ltr',
                'numbering_system': 'latn',
                'week_start': 1,
                'font_family_key': 'sans',
                'completeness_pct': 100.0,
                'review_status': 'reviewed',
                'sort_order': 3,
            },
            {
                'code': 'en-IN',
                'name': 'English (India)',
                'native_name': 'English (IN)',
                'direction': 'ltr',
                'numbering_system': 'latn',
                'week_start': 1,
                'font_family_key': 'sans',
                'completeness_pct': 100.0,
                'review_status': 'reviewed',
                'sort_order': 4,
            },
        ]
        for spec in languages:
            obj, created = Language.objects.update_or_create(
                code=spec['code'],
                defaults=spec,
            )
            action = "Created" if created else "Updated/Verified"
            self.stdout.write(f"  [{action}] Language: {obj.native_name} ({obj.code})")

    def seed_policy_settings(self):
        settings, created = PolicySettings.objects.get_or_create(
            pk=1,
            defaults={
                'max_call_attempts_before_unreachable': 5,
                'unreachable_followup_days': 14,
                'nurture_default_days': 90,
                'who_can_mark_lost': 'manager',
            }
        )
        action = "Created" if created else "Verified"
        self.stdout.write(f"  [{action}] PolicySettings: {settings}")

    def seed_lost_reasons(self):
        reasons = [
            ('price_too_high', 'price too high', {'hi': {'name': 'कीमत बहुत अधिक है'}, 'en-AU': {'name': 'Price too high'}}),
            ('chose_competitor', 'chose a competitor', {'hi': {'name': 'प्रतिस्पर्धी को चुना'}, 'en-AU': {'name': 'Chose a competitor'}}),
            ('not_interested', 'not interested', {'hi': {'name': 'रुचि नहीं है'}, 'en-AU': {'name': 'Not interested'}}),
            ('no_response', 'no response', {'hi': {'name': 'कोई प्रतिक्रिया नहीं'}, 'en-AU': {'name': 'No response'}}),
            ('not_owner', 'not the owner', {'hi': {'name': 'मकान मालिक नहीं है'}, 'en-AU': {'name': 'Not the homeowner'}}),
            ('no_suitable_roof', 'no suitable roof', {'hi': {'name': 'छत उपयुक्त नहीं है'}, 'en-AU': {'name': 'No suitable roof'}}),
            ('already_installed', 'already installed', {'hi': {'name': 'पहले से स्थापित है'}, 'en-AU': {'name': 'Already installed'}}),
            ('bought_elsewhere', 'bought elsewhere', {'hi': {'name': 'कहीं और से खरीदा'}, 'en-AU': {'name': 'Bought elsewhere'}}),
            ('trust_or_brand_concern', 'trust or brand concern', {'hi': {'name': 'ब्रांड या विश्वास की चिंता'}, 'en-AU': {'name': 'Brand concern'}}),
            ('wrong_or_invalid_contact', 'wrong or invalid contact', {'hi': {'name': 'गलत संपर्क जानकारी'}, 'en-AU': {'name': 'Invalid contact'}}),
            ('other', 'other', {'hi': {'name': 'अन्य'}, 'en-AU': {'name': 'Other'}}),
        ]
        for idx, (code, name, trans) in enumerate(reasons, start=1):
            obj, created = LostReason.objects.update_or_create(
                name=name,
                defaults={
                    'code': code,
                    'translations': trans,
                    'sort_order': idx,
                    'is_active': True,
                },
            )
            action = "Created" if created else "Updated/Verified"
            self.stdout.write(f"  [{action}] LostReason: {obj.name} ({obj.code})")

    def seed_nurture_reasons(self):
        reasons = [
            ('not_now', 'not now', {'hi': {'name': 'अभी नहीं'}, 'en-AU': {'name': 'Not now'}}),
            ('waiting_budget', 'waiting for budget', {'hi': {'name': 'बजट की प्रतीक्षा'}, 'en-AU': {'name': 'Waiting for budget'}}),
            ('waiting_loan', 'waiting for a loan', {'hi': {'name': 'ऋण (लोन) की प्रतीक्षा'}, 'en-AU': {'name': 'Waiting for finance'}}),
            ('waiting_family', 'waiting for the owner or family', {'hi': {'name': 'परिवार या मालिक से चर्चा'}, 'en-AU': {'name': 'Consulting family'}}),
            ('under_construction', 'house under construction', {'hi': {'name': 'मकान निर्माणाधीन है'}, 'en-AU': {'name': 'Home under construction'}}),
            ('compare_later', 'wants to compare later', {'hi': {'name': 'बाद में तुलना करना चाहते हैं'}, 'en-AU': {'name': 'Comparing quotes'}}),
        ]
        for idx, (code, name, trans) in enumerate(reasons, start=1):
            obj, created = NurtureReason.objects.update_or_create(
                name=name,
                defaults={
                    'code': code,
                    'translations': trans,
                    'sort_order': idx,
                    'is_active': True,
                },
            )
            action = "Created" if created else "Updated/Verified"
            self.stdout.write(f"  [{action}] NurtureReason: {obj.name} ({obj.code})")

    def seed_lead_sources(self):
        sources = [
            ('website_form', 'Website form', {'hi': {'name': 'वेबसाइट फॉर्म'}, 'en-AU': {'name': 'Website Enquiry'}}),
            ('meta_ads', 'Meta ads', {'hi': {'name': 'मेटा विज्ञापन'}, 'en-AU': {'name': 'Social Media Ads'}}),
            ('google_ads', 'Google ads', {'hi': {'name': 'गूगल विज्ञापन'}, 'en-AU': {'name': 'Google Ads'}}),
            ('referral', 'Referral', {'hi': {'name': 'सिफारिश (रेफरल)'}, 'en-AU': {'name': 'Referral'}}),
            ('walk_in', 'Walk-in', {'hi': {'name': 'सीधे संपर्क'}, 'en-AU': {'name': 'Direct Inbound'}}),
            ('other', 'Other', {'hi': {'name': 'अन्य'}, 'en-AU': {'name': 'Other'}}),
        ]
        for idx, (code, name, trans) in enumerate(sources, start=1):
            obj, created = LeadSource.objects.update_or_create(
                name=name,
                defaults={
                    'code': code,
                    'translations': trans,
                    'sort_order': idx,
                    'is_active': True,
                },
            )
            action = "Created" if created else "Updated/Verified"
            self.stdout.write(f"  [{action}] LeadSource: {obj.name} ({obj.code})")

    def seed_outcomes(self):
        call_outcomes = [
            {
                'code': 'NO_ANSWER',
                'name': 'No answer',
                'translations': {'hi': {'name': 'उत्तर नहीं मिला', 'next_action': 'पुनः प्रयास करें, फिर व्हाट्सएप भेजें'}},
                'default_status': 'Attempting contact',
                'default_next_action': 'Retry, then WhatsApp',
                'default_followup_days': 0,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 1,
            },
            {
                'code': 'BUSY_SWITCHED_OFF',
                'name': 'Busy or switched off',
                'translations': {'hi': {'name': 'व्यस्त या स्विच ऑफ', 'next_action': 'दूसरे समय पुनः प्रयास करें'}},
                'default_status': 'Attempting contact',
                'default_next_action': 'Retry at a different time',
                'default_followup_days': 1,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 2,
            },
            {
                'code': 'CALL_LATER',
                'name': 'Customer asks to call later',
                'translations': {'hi': {'name': 'ग्राहक ने बाद में कॉल करने को कहा', 'next_action': 'ग्राहक द्वारा दिए गए समय पर कॉल करें'}},
                'default_status': 'Callback scheduled',
                'default_next_action': 'Call at the time customer gave',
                'default_followup_days': None,
                'followup_date_required_manually': True,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 3,
            },
            {
                'code': 'WRONG_INVALID_NUMBER',
                'name': 'Wrong or invalid number',
                'translations': {'hi': {'name': 'गलत या अमान्य नंबर', 'next_action': 'फॉर्म या स्रोत से अन्य नंबर जांचें'}},
                'default_status': 'Invalid contact',
                'default_next_action': 'Check form or source for another number',
                'default_followup_days': None,
                'followup_date_required_manually': False,
                'is_terminal': True,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 4,
            },
            {
                'code': 'NOT_DECISION_MAKER',
                'name': 'Not the decision maker',
                'translations': {'hi': {'name': 'निर्णय लेने वाला व्यक्ति नहीं', 'next_action': 'निर्णय लेने वाले का नंबर या उपयुक्त समय पूछें'}},
                'default_status': 'Follow-up',
                'default_next_action': "Ask for decision maker's number or best time",
                'default_followup_days': 2,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 5,
            },
            {
                'code': 'INTERESTED_MORE_INFO',
                'name': 'Interested, wants more information',
                'translations': {'hi': {'name': 'रुचि है, अधिक जानकारी चाहिए', 'next_action': 'विवरण, ब्रोशर या बचत उदाहरण व्हाट्सएप पर भेजें'}},
                'default_status': 'Interested',
                'default_next_action': 'Send details, brochure or sample savings on WhatsApp',
                'default_followup_days': 2,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 6,
            },
            {
                'code': 'AGREES_SURVEY',
                'name': 'Agrees, ready for site survey',
                'translations': {'hi': {'name': 'सहमत, साइट सर्वे के लिए तैयार', 'next_action': 'सर्वेक्षण तिथि बुक करें और पुष्टि भेजें'}},
                'default_status': 'Survey to schedule',
                'default_next_action': 'Book survey date and send confirmation',
                'default_followup_days': None,
                'followup_date_required_manually': True,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 7,
            },
            {
                'code': 'DISCUSS_FAMILY',
                'name': 'Wants to discuss with family',
                'translations': {'hi': {'name': 'परिवार से चर्चा करना चाहते हैं', 'next_action': 'परिवार के साथ कॉल या लघु प्रस्तुति का प्रस्ताव दें'}},
                'default_status': 'Follow-up',
                'default_next_action': 'Offer a call with the family or a short presentation',
                'default_followup_days': 3,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 8,
            },
            {
                'code': 'BUDGET_CONCERN',
                'name': 'Price or budget concern',
                'translations': {'hi': {'name': 'कीमत या बजट की चिंता', 'next_action': 'वित्तपोषण, सब्सिडी और पेबैक विवरण साझा करें'}},
                'default_status': 'Interested',
                'default_next_action': 'Share financing, subsidy and payback details',
                'default_followup_days': 3,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 9,
            },
            {
                'code': 'NOT_INTERESTED_NOW',
                'name': 'Not interested for now',
                'translations': {'hi': {'name': 'अभी रुचि नहीं है', 'next_action': 'पूछें कब पुनः संपर्क करें, कारण दर्ज करें'}},
                'default_status': 'Nurture',
                'default_next_action': 'Ask when to contact again, record the reason',
                'default_followup_days': 90,
                'followup_date_required_manually': True,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': True,
                'sort_order': 10,
            },
            {
                'code': 'NOT_INTERESTED_ALL',
                'name': 'Not interested at all',
                'translations': {'hi': {'name': 'बिल्कुल रुचि नहीं है', 'next_action': 'कारण दर्ज करें'}},
                'default_status': 'Lost',
                'default_next_action': 'Record the reason (price, competitor, timing, trust, other)',
                'default_followup_days': None,
                'followup_date_required_manually': False,
                'is_terminal': True,
                'requires_lost_reason': True,
                'requires_nurture_reason': False,
                'sort_order': 11,
            },
            {
                'code': 'ALREADY_INSTALLED',
                'name': 'Already installed solar or booked with someone else',
                'translations': {'hi': {'name': 'सोलर लग चुका है या अन्य जगह बुक किया', 'next_action': 'कारण और विवरण दर्ज करें'}},
                'default_status': 'Lost',
                'default_next_action': 'Record installer, size and reason if customer shares it',
                'default_followup_days': None,
                'followup_date_required_manually': False,
                'is_terminal': True,
                'requires_lost_reason': True,
                'requires_nurture_reason': False,
                'sort_order': 12,
            },
            {
                'code': 'NOT_OWNER_NO_ROOF',
                'name': 'Not the owner, rented house or no suitable roof',
                'translations': {'hi': {'name': 'मालिक नहीं या उपयुक्त छत नहीं', 'next_action': 'मालिक का विवरण पूछें या कारण दर्ज करें'}},
                'default_status': 'Follow-up',
                'default_next_action': 'Ask for owner details or record the roof issue, else mark lost',
                'default_followup_days': 2,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 13,
            },
            {
                'code': 'DO_NOT_CONTACT',
                'name': 'Asked not to be called again',
                'translations': {'hi': {'name': 'दोबारा कॉल न करने को कहा', 'next_action': 'डीएनसी सूची में तुरंत जोड़ें'}},
                'default_status': 'Do not contact',
                'default_next_action': 'Set do not contact, do not call or message again',
                'default_followup_days': None,
                'followup_date_required_manually': False,
                'is_terminal': True,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 14,
            },
            {
                'code': 'DUPLICATE_ENQUIRY',
                'name': 'Duplicate enquiry',
                'translations': {'hi': {'name': 'डुप्लिकेट पूछताछ', 'next_action': 'मौजूदा लीड के साथ मर्ज करें'}},
                'default_status': 'Merged',
                'default_next_action': 'Find the primary lead and merge, keep the newest notes',
                'default_followup_days': None,
                'followup_date_required_manually': False,
                'is_terminal': True,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 15,
            },
        ]

        survey_outcomes = [
            {
                'code': 'SURVEY_BOOKED',
                'name': 'Survey booked',
                'translations': {'hi': {'name': 'सर्वेक्षण बुक हुआ', 'next_action': 'सर्वेक्षक नियुक्त करें'}},
                'default_status': 'Survey scheduled',
                'default_next_action': 'Assign surveyor and confirm the time',
                'default_followup_days': None,
                'followup_date_required_manually': True,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 1,
            },
            {
                'code': 'SURVEY_RESCHEDULE',
                'name': 'Customer asks to reschedule',
                'translations': {'hi': {'name': 'ग्राहक ने पुनर्निर्धारित करने को कहा', 'next_action': 'नया समय तय करें'}},
                'default_status': 'Survey rescheduled',
                'default_next_action': 'Pick a new date and time',
                'default_followup_days': None,
                'followup_date_required_manually': True,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 2,
            },
            {
                'code': 'SURVEY_CUSTOMER_UNREACHABLE',
                'name': 'Customer not at site or not reachable on the day',
                'translations': {'hi': {'name': 'ग्राहक साइट पर नहीं या संपर्क नहीं हुआ', 'next_action': 'कॉल करके नया समय तय करें'}},
                'default_status': 'Survey missed',
                'default_next_action': 'Call the customer and set a new date, retry up to the policy limit',
                'default_followup_days': 1,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 3,
            },
            {
                'code': 'SURVEYOR_DELAYED',
                'name': 'Surveyor cancels or is delayed',
                'translations': {'hi': {'name': 'सर्वेयर देरी या रद्द', 'next_action': 'ग्राहक को सूचित करें और पुनः बुक करें'}},
                'default_status': 'Survey rescheduled',
                'default_next_action': 'Inform customer right away and pick the next slot',
                'default_followup_days': 1,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 4,
            },
            {
                'code': 'SURVEY_DONE_SUITABLE',
                'name': 'Survey done, site suitable',
                'translations': {'hi': {'name': 'सर्वे पूरा, साइट उपयुक्त', 'next_action': 'डिजाइन और कोटेशन तैयार करें'}},
                'default_status': 'Design pending',
                'default_next_action': 'Prepare the design and quotation',
                'default_followup_days': 2,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 5,
            },
            {
                'code': 'SURVEY_DONE_UNSUITABLE',
                'name': 'Survey done, site not suitable (shade, weak roof, no space)',
                'translations': {'hi': {'name': 'सर्वे पूरा, साइट उपयुक्त नहीं', 'next_action': 'विकल्प समझाएं या कारण दर्ज करें'}},
                'default_status': 'Alternative',
                'default_next_action': 'Explain, offer a smaller system or another option, else record lost reason',
                'default_followup_days': 2,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 6,
            },
            {
                'code': 'SURVEY_CHANGES_MIND',
                'name': 'Customer changes mind before the survey',
                'translations': {'hi': {'name': 'सर्वे से पहले ग्राहक का विचार बदला', 'next_action': 'कारण और अगली तिथि दर्ज करें'}},
                'default_status': 'Nurture',
                'default_next_action': 'Record the reason and next date',
                'default_followup_days': 90,
                'followup_date_required_manually': True,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': True,
                'sort_order': 7,
            },
        ]

        quote_outcomes = [
            {
                'code': 'QUOTE_SENT_NO_REPLY',
                'name': 'Quote sent, no reply',
                'translations': {'hi': {'name': 'कोटेशन भेजा, कोई जवाब नहीं', 'next_action': 'कॉल और व्हाट्सएप द्वारा फॉलो-अप करें'}},
                'default_status': 'Quote sent',
                'default_next_action': 'Follow up by call and WhatsApp on a set schedule',
                'default_followup_days': 2,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 1,
            },
            {
                'code': 'QUOTE_QUESTIONS',
                'name': 'Customer asks questions',
                'translations': {'hi': {'name': 'ग्राहक के प्रश्न हैं', 'next_action': 'उत्तर दें और छूटे हुए विवरण भेजें'}},
                'default_status': 'Follow-up',
                'default_next_action': 'Answer and send missing details',
                'default_followup_days': 1,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 2,
            },
            {
                'code': 'QUOTE_REVISION',
                'name': 'Customer asks for changes (size, brand, price)',
                'translations': {'hi': {'name': 'संशोधन की मांग (आकार, ब्रांड, कीमत)', 'next_action': 'संशोधित कोटेशन भेजें'}},
                'default_status': 'Revising quote',
                'default_next_action': 'Send a revised quote and keep the old version',
                'default_followup_days': 1,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 3,
            },
            {
                'code': 'QUOTE_NEGOTIATION',
                'name': 'Customer compares with another vendor',
                'translations': {'hi': {'name': 'अन्य वेंडर से तुलना / बातचीत', 'next_action': 'वारंटी और सेवा में अंतर साझा करें'}},
                'default_status': 'Negotiation',
                'default_next_action': 'Share differences in warranty, service and quality',
                'default_followup_days': 2,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 4,
            },
            {
                'code': 'QUOTE_WAIT',
                'name': 'Customer wants to wait',
                'translations': {'hi': {'name': 'ग्राहक प्रतीक्षा करना चाहता है', 'next_action': 'कारण और पुनः कॉल तिथि दर्ज करें'}},
                'default_status': 'Nurture',
                'default_next_action': 'Record the reason and the date to call back',
                'default_followup_days': 90,
                'followup_date_required_manually': True,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': True,
                'sort_order': 5,
            },
            {
                'code': 'QUOTE_WON',
                'name': 'Customer agrees',
                'translations': {'hi': {'name': 'ग्राहक सहमत है', 'next_action': 'प्रक्रिया समाप्त'}},
                'default_status': 'Won',
                'default_next_action': 'Process ends here',
                'default_followup_days': None,
                'followup_date_required_manually': False,
                'is_terminal': True,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 6,
            },
            {
                'code': 'QUOTE_LOST',
                'name': 'Customer rejects',
                'translations': {'hi': {'name': 'ग्राहक ने अस्वीकार किया', 'next_action': 'कारण दर्ज करें'}},
                'default_status': 'Lost',
                'default_next_action': 'Record the reason (price, competitor, trust, timing, other)',
                'default_followup_days': None,
                'followup_date_required_manually': False,
                'is_terminal': True,
                'requires_lost_reason': True,
                'requires_nurture_reason': False,
                'sort_order': 7,
            },
        ]

        stages = [
            (Outcome.Stage.CALL, call_outcomes),
            (Outcome.Stage.SURVEY, survey_outcomes),
            (Outcome.Stage.QUOTE, quote_outcomes),
        ]

        for stage, outcome_list in stages:
            for item in outcome_list:
                obj, created = Outcome.objects.update_or_create(
                    stage=stage,
                    name=item['name'],
                    defaults={
                        'code': item['code'],
                        'translations': item['translations'],
                        'default_status': item['default_status'],
                        'default_next_action': item['default_next_action'],
                        'default_followup_days': item['default_followup_days'],
                        'followup_date_required_manually': item['followup_date_required_manually'],
                        'is_terminal': item['is_terminal'],
                        'requires_lost_reason': item['requires_lost_reason'],
                        'requires_nurture_reason': item['requires_nurture_reason'],
                        'sort_order': item['sort_order'],
                        'is_active': True,
                    }
                )
                action = 'Created' if created else 'Updated/Verified'
                self.stdout.write(f'  [{action}] Outcome [{stage}]: {obj.name} ({obj.code})')

    def seed_regions_translations(self):
        in_trans = {
            'hi': {
                'name': 'भारत',
                'tax_label': 'जीएसटी',
                'incentive_label': 'सब्सिडी (पीएम सूर्य घर)',
                'electricity_provider_label': 'डिस्कॉम',
                'opt_out_text': 'संदेश रोकने के लिए STOP लिखकर भेजें',
                'privacy_notice_text': 'हम डीपीडीपी अधिनियम 2023 के तहत संपर्क विवरण सुरक्षित रखते हैं।',
                'region_notes': 'पीएम सूर्य घर मुफ्त बिजली योजना 3 किलोवाट तक ₹78,000 की वित्तीय सहायता प्रदान करती है।',
            }
        }
        Region.objects.filter(code='IN').update(
            default_language='hi',
            translations=in_trans,
        )

        au_trans = {
            'en-AU': {
                'name': 'Australia',
                'incentive_label': 'Government incentive (STCs and rebates)',
                'electricity_provider_label': 'Electricity Retailer',
            }
        }
        Region.objects.filter(code='AU').update(
            default_language='en',
            translations=au_trans,
        )
        self.stdout.write("  [Updated/Verified] Region translations & default languages for IN and AU.")

    def seed_roof_and_property_types(self):
        reg_in = Region.objects.filter(code='IN').first()
        reg_au = Region.objects.filter(code='AU').first()

        roofs_in = [
            ('rcc_flat', 'RCC flat', {'hi': {'name': 'आरसीसी फ्लैट छत'}}),
            ('tin_shade', 'tin shade', {'hi': {'name': 'टिन शेड छत'}}),
            ('slanted_tile', 'slanted tile', {'hi': {'name': 'ढलान वाली खपरैल छत'}}),
        ]
        if reg_in:
            for code, name, trans in roofs_in:
                RoofType.objects.update_or_create(
                    region=reg_in,
                    name=name,
                    defaults={'code': code, 'translations': trans, 'is_active': True},
                )

        roofs_au = [
            ('colorbond', 'Colorbond', {'en-AU': {'name': 'Colorbond Metal'}}),
            ('tile', 'Tile', {'en-AU': {'name': 'Terracotta / Concrete Tile'}}),
            ('tin', 'Tin', {'en-AU': {'name': 'Corrugated Tin'}}),
            ('slate', 'Slate', {'en-AU': {'name': 'Slate Roof'}}),
        ]
        if reg_au:
            for code, name, trans in roofs_au:
                RoofType.objects.update_or_create(
                    region=reg_au,
                    name=name,
                    defaults={'code': code, 'translations': trans, 'is_active': True},
                )

        props = [
            ('residential', 'residential', {'hi': {'name': 'आवासीय'}, 'en-AU': {'name': 'Residential'}}),
            ('commercial', 'commercial', {'hi': {'name': 'व्यावसायिक'}, 'en-AU': {'name': 'Commercial'}}),
            ('industrial', 'industrial', {'hi': {'name': 'औद्योगिक'}, 'en-AU': {'name': 'Industrial'}}),
            ('agricultural', 'agricultural', {'hi': {'name': 'कृषि'}, 'en-AU': {'name': 'Agricultural'}}),
        ]
        for reg in [reg_in, reg_au]:
            if not reg:
                continue
            for code, name, trans in props:
                PropertyType.objects.update_or_create(
                    region=reg,
                    name=name,
                    defaults={'code': code, 'translations': trans, 'is_active': True},
                )
        self.stdout.write("  [Updated/Verified] RoofType & PropertyType codes & translations.")

    def seed_initial_translation_entries(self):
        sample_entries = [
            # common
            ('hi', 'common', 'app_name', 'Solar CRM', 'सोलर सीआरएम', 'reviewed', False),
            ('hi', 'common', 'save', 'Save', 'सहेजें', 'reviewed', False),
            ('hi', 'common', 'cancel', 'Cancel', 'रद्द करें', 'reviewed', False),
            ('hi', 'common', 'delete', 'Delete', 'हटाएं', 'reviewed', False),
            ('hi', 'common', 'edit', 'Edit', 'संपादित करें', 'reviewed', False),
            ('hi', 'common', 'search', 'Search', 'खोजें...', 'reviewed', False),
            ('hi', 'common', 'loading', 'Loading...', 'लोड हो रहा है...', 'reviewed', False),
            ('hi', 'common', 'success', 'Success', 'सफलता', 'reviewed', False),
            ('hi', 'common', 'error', 'Error', 'त्रुटि', 'reviewed', False),
            ('hi', 'common', 'confirm', 'Confirm', 'पुष्टि करें', 'reviewed', False),
            # auth
            ('hi', 'auth', 'login_title', 'Sign in to Solar CRM', 'सोलर सीआरएम में साइन इन करें', 'reviewed', False),
            ('hi', 'auth', 'username', 'Username', 'उपयोगकर्ता नाम (यूज़रनेम)', 'reviewed', False),
            ('hi', 'auth', 'password', 'Password', 'पासवर्ड', 'reviewed', False),
            ('hi', 'auth', 'signin_btn', 'Sign in', 'साइन इन करें', 'reviewed', False),
            ('hi', 'auth', 'forgot_password', 'Forgot password?', 'पासवर्ड भूल गए?', 'reviewed', False),
            # nav / sidebar
            ('hi', 'nav', 'dashboard', 'Dashboard', 'डैशबोर्ड', 'reviewed', False),
            ('hi', 'nav', 'leads', 'Leads', 'लीड्स (ग्राहक)', 'reviewed', False),
            ('hi', 'nav', 'surveys', 'Site Surveys', 'साइट सर्वेक्षण', 'reviewed', False),
            ('hi', 'nav', 'quotes', 'Quotes', 'कोटेशन और प्रस्ताव', 'reviewed', False),
            ('hi', 'nav', 'today', 'Today', 'आज का कार्य', 'reviewed', False),
            ('hi', 'nav', 'attention', 'Attention Needed', 'ध्यान देने योग्य', 'reviewed', False),
            ('hi', 'nav', 'admin', 'Admin Settings', 'प्रशासन सेटिंग्स', 'reviewed', False),
            # customer templates
            ('hi', 'customer', 'opt_out', 'Reply STOP to opt out', 'संदेश रोकने के लिए STOP लिखकर भेजें', 'reviewed', True),
            ('hi', 'customer', 'survey_confirm', 'Your site survey is booked for {time}.', 'आपका साइट सर्वेक्षण {time} के लिए निर्धारित किया गया है।', 'reviewed', True),
        ]
        for lang, ns, key, en_text, hi_text, status, cust_facing in sample_entries:
            TranslationEntry.objects.update_or_create(
                language=lang,
                namespace=ns,
                key=key,
                defaults={
                    'english_text': en_text,
                    'translated_text': hi_text,
                    'status': status,
                    'is_customer_facing': cust_facing,
                }
            )
        self.stdout.write(f"  [Seeded] {len(sample_entries)} initial translation catalog entries in database.")
