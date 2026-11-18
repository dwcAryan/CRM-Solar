import json
import logging

from django.core.management.base import BaseCommand

from helpbot.nlp import (
    DYNAMIC_FACTS_FILE,
    IntentEngine,
    KnowledgeRetriever,
)
from masters.models import LostReason, Outcome, PolicySettings, Region

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Builds the Helpbot knowledge index and trains the intent classifier using live database policy settings."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force retraining and rebuilding even if cached models exist',
        )

    def handle(self, *args, **options):
        self.stdout.write("Gathering live dynamic facts from database...")
        facts = []

        # 1. Policy Settings
        try:
            policy = PolicySettings.objects.first()
            if policy:
                facts.append({
                    'id': 'fact_policy_unreachable',
                    'topic': 'retry_rules',
                    'title': 'Live Policy: Max Call Attempts',
                    'content': f"According to current live Policy Settings, a lead is automatically moved to Unreachable after {policy.max_call_attempts_before_unreachable} failed call attempts, with a default follow-up of {policy.unreachable_followup_days} days.",
                    'roles': ['admin', 'manager', 'salesperson'],
                    'regions': ['IN', 'AU'],
                })
                facts.append({
                    'id': 'fact_policy_mark_lost',
                    'topic': 'lost_rules',
                    'title': 'Live Policy: Authority to Mark Lost',
                    'content': f"According to current live Policy Settings, 'who_can_mark_lost' is set to '{policy.who_can_mark_lost}'. Users must have the role of {policy.who_can_mark_lost} or higher to mark leads as Lost.",
                    'roles': ['admin', 'manager', 'salesperson'],
                    'regions': ['IN', 'AU'],
                })
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not load PolicySettings: {e}"))

        # 2. Regions
        try:
            regions = Region.objects.filter(is_active=True)
            for r in regions:
                facts.append({
                    'id': f"fact_region_{r.code.lower()}",
                    'topic': 'regions_compliance',
                    'title': f"Live Region Setting: {r.name} ({r.code})",
                    'content': (
                        f"Region {r.name} ({r.code}) uses currency {r.currency} ({r.currency_symbol}), "
                        f"dialing prefix {r.phone_country_code}, timezone {r.default_timezone}, "
                        f"tax label '{r.tax_label}' ({float(r.tax_rate)*100:.1f}%), "
                        f"incentive label '{r.incentive_label}', and electricity provider label '{r.electricity_provider_label}'."
                    ),
                    'roles': ['admin', 'manager', 'salesperson'],
                    'regions': [r.code],
                })
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not load Regions: {e}"))

        # 3. Outcomes
        try:
            outcomes = Outcome.objects.filter(is_active=True)
            call_outcomes = [o.name for o in outcomes if o.stage == 'call']
            if call_outcomes:
                facts.append({
                    'id': 'fact_call_outcomes_list',
                    'topic': 'call_outcomes',
                    'title': 'Live Configured Call Outcomes',
                    'content': f"Active call outcomes configured in the system are: {', '.join(call_outcomes)}.",
                    'roles': ['admin', 'manager', 'salesperson'],
                    'regions': ['IN', 'AU'],
                })
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not load Outcomes: {e}"))

        # 4. Lost Reasons
        try:
            lost_reasons = LostReason.objects.filter(is_active=True).values_list('name', flat=True)
            if lost_reasons:
                facts.append({
                    'id': 'fact_lost_reasons_list',
                    'topic': 'lost_rules',
                    'title': 'Live Configured Lost Reasons',
                    'content': f"Active reasons for closing a lead as Lost are: {', '.join(lost_reasons)}.",
                    'roles': ['admin', 'manager', 'salesperson'],
                    'regions': ['IN', 'AU'],
                })
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not load LostReasons: {e}"))

        # Save dynamic facts
        DYNAMIC_FACTS_FILE.parent.mkdir(exist_ok=True)
        with open(DYNAMIC_FACTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(facts, f, indent=2)
        self.stdout.write(self.style.SUCCESS(f"Saved {len(facts)} dynamic facts to {DYNAMIC_FACTS_FILE}"))

        # Train Intent Classifier
        self.stdout.write("Training intent classifier...")
        engine = IntentEngine()
        engine.train()
        self.stdout.write(self.style.SUCCESS("Intent classifier trained and saved successfully."))

        # Build Knowledge Index
        self.stdout.write("Building BM25 knowledge index...")
        retriever = KnowledgeRetriever()
        retriever.build_index()
        self.stdout.write(self.style.SUCCESS(f"BM25 index built with {len(retriever.documents)} passages."))

        self.stdout.write(self.style.SUCCESS("Helpbot indexing and model training complete!"))
