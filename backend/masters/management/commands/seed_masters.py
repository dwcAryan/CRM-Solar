from django.core.management.base import BaseCommand
from django.db import transaction

from masters.models import LeadSource, LostReason, NurtureReason, Outcome, PolicySettings


class Command(BaseCommand):
    help = "Seeds master data (Outcomes, LostReasons, NurtureReasons, LeadSources, PolicySettings) idempotently."

    def handle(self, *args, **options):
        self.stdout.write("Seeding master tables...")

        with transaction.atomic():
            self.seed_policy_settings()
            self.seed_lost_reasons()
            self.seed_nurture_reasons()
            self.seed_lead_sources()
            self.seed_outcomes()

        self.stdout.write(self.style.SUCCESS("Master data seeded successfully and idempotently."))

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
            'price too high',
            'chose a competitor',
            'not interested',
            'no response',
            'not the owner',
            'no suitable roof',
            'already installed',
            'bought elsewhere',
            'trust or brand concern',
            'wrong or invalid contact',
            'other',
        ]
        for idx, name in enumerate(reasons, start=1):
            obj, created = LostReason.objects.update_or_create(
                name=name,
                defaults={'sort_order': idx, 'is_active': True},
            )
            action = "Created" if created else "Updated/Verified"
            self.stdout.write(f"  [{action}] LostReason: {obj.name}")

    def seed_nurture_reasons(self):
        reasons = [
            'not now',
            'waiting for budget',
            'waiting for a loan',
            'waiting for the owner or family',
            'house under construction',
            'wants to compare later',
        ]
        for idx, name in enumerate(reasons, start=1):
            obj, created = NurtureReason.objects.update_or_create(
                name=name,
                defaults={'sort_order': idx, 'is_active': True},
            )
            action = "Created" if created else "Updated/Verified"
            self.stdout.write(f"  [{action}] NurtureReason: {obj.name}")

    def seed_lead_sources(self):
        sources = [
            'Website form',
            'Meta ads',
            'Google ads',
            'Referral',
            'Walk-in',
            'Other',
        ]
        for idx, name in enumerate(sources, start=1):
            obj, created = LeadSource.objects.update_or_create(
                name=name,
                defaults={'sort_order': idx, 'is_active': True},
            )
            action = "Created" if created else "Updated/Verified"
            self.stdout.write(f"  [{action}] LeadSource: {obj.name}")

    def seed_outcomes(self):
        call_outcomes = [
            {
                'name': 'No answer',
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
                'name': 'Busy or switched off',
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
                'name': 'Customer asks to call later',
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
                'name': 'Wrong or invalid number',
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
                'name': 'Not the decision maker',
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
                'name': 'Interested, wants more information',
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
                'name': 'Agrees, ready for site survey',
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
                'name': 'Wants to discuss with family',
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
                'name': 'Price or budget concern',
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
                'name': 'Not interested for now',
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
                'name': 'Not interested at all',
                'default_status': 'Lost',
                'default_next_action': 'Record the lost reason',
                'default_followup_days': None,
                'followup_date_required_manually': False,
                'is_terminal': True,
                'requires_lost_reason': True,
                'requires_nurture_reason': False,
                'sort_order': 11,
            },
            {
                'name': 'Already installed solar or booked with someone else',
                'default_status': 'Lost',
                'default_next_action': 'Record reason, ask for a referral',
                'default_followup_days': None,
                'followup_date_required_manually': False,
                'is_terminal': True,
                'requires_lost_reason': True,
                'requires_nurture_reason': False,
                'sort_order': 12,
            },
            {
                'name': 'Not the owner, rented house or no suitable roof',
                'default_status': 'Follow-up',
                'default_next_action': 'Ask whether the owner can be contacted',
                'default_followup_days': 2,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 13,
            },
            {
                'name': 'Asked not to be called again',
                'default_status': 'Do not contact',
                'default_next_action': 'Block calls and messages',
                'default_followup_days': None,
                'followup_date_required_manually': False,
                'is_terminal': True,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 14,
            },
            {
                'name': 'Duplicate enquiry',
                'default_status': 'Merged',
                'default_next_action': 'Merge with the existing record',
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
                'name': 'Survey booked',
                'default_status': 'Survey scheduled',
                'default_next_action': 'Send reminder the day before',
                'default_followup_days': None,
                'followup_date_required_manually': True,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 1,
            },
            {
                'name': 'Customer asks to reschedule',
                'default_status': 'Survey rescheduled',
                'default_next_action': 'Book a new date, update reminder',
                'default_followup_days': None,
                'followup_date_required_manually': True,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 2,
            },
            {
                'name': 'Customer not at site or not reachable on the day',
                'default_status': 'Survey missed',
                'default_next_action': 'Call, rebook, note the missed visit',
                'default_followup_days': 1,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 3,
            },
            {
                'name': 'Surveyor cancels or is delayed',
                'default_status': 'Survey rescheduled',
                'default_next_action': 'Inform the customer and rebook',
                'default_followup_days': 1,
                'followup_date_required_manually': False,
                'is_terminal': False,
                'requires_lost_reason': False,
                'requires_nurture_reason': False,
                'sort_order': 4,
            },
            {
                'name': 'Survey done, site suitable',
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
                'name': 'Survey done, site not suitable (shade, weak roof, no space)',
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
                'name': 'Customer changes mind before the survey',
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
                'name': 'Quote sent, no reply',
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
                'name': 'Customer asks questions',
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
                'name': 'Customer asks for changes (size, brand, price)',
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
                'name': 'Customer compares with another vendor',
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
                'name': 'Customer wants to wait',
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
                'name': 'Customer agrees',
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
                'name': 'Customer rejects',
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
                action = "Created" if created else "Updated/Verified"
                self.stdout.write(f"  [{action}] Outcome [{stage}]: {obj.name} -> {obj.default_status}")
