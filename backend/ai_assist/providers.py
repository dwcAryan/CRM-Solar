"""
AI and Rule-Based Providers for Solar CRM AI Assist.
Implements Abstract Provider, Anthropic Messages API Provider, and Rules Fallback Provider.
"""

from __future__ import annotations

import abc
import json
import logging
import re
from typing import Any

from django.conf import settings

from .prompts import SOLAR_SALES_COACH_SYSTEM_PROMPT, build_sales_coach_user_prompt

logger = logging.getLogger(__name__)


class AISuggestionProvider(abc.ABC):
    """Abstract base class for AI suggestion providers."""

    @abc.abstractmethod
    def generate(self, context: dict[str, Any]) -> tuple[dict[str, Any], int]:
        """
        Generates sales coaching recommendations for a lead.
        Returns: (output_dict, tokens_used)
        """
        raise NotImplementedError


class RulesProvider(AISuggestionProvider):
    """
    Deterministic, rule-based sales coach provider.
    Provides intelligent recommendations tailored to Indian rooftop solar sales
    without requiring external API calls or API keys.
    """

    def generate(self, context: dict[str, Any]) -> tuple[dict[str, Any], int]:
        first_name = context.get("first_name", "Customer")
        city = context.get("city", "your city")
        status = context.get("status", "New")
        attempt_count = context.get("attempt_count", 0)
        recent_activities = context.get("recent_activities", [])
        quotes = context.get("quotes", [])
        monthly_bill = context.get("monthly_bill")
        roof_type = context.get("roof_type", "RCC")

        latest_outcome = recent_activities[0]["outcome"] if recent_activities else ""

        # Case 1: 3 or more failed call attempts
        if attempt_count >= 3 or latest_outcome in ["No answer", "Busy or switched off"]:
            return {
                "situation_summary": (
                    f"{first_name} has missed {attempt_count} consecutive call attempts with no direct phone response. "
                    "Repeated calling at the same hour will likely be perceived as spam."
                ),
                "risk_level": "high" if attempt_count >= 4 else "medium",
                "risk_reason": f"{attempt_count} unanswered outreach attempts indicate communication friction or bad call timing.",
                "best_next_action": "Switch channel to WhatsApp with a brief polite note and schedule callback in the evening.",
                "suggested_follow_up_timing": "Today between 6:30 PM and 8:00 PM (after work hours)",
                "suggested_outcome_to_log": "Busy or switched off" if attempt_count < 5 else "No answer",
                "talking_points": [
                    f"Acknowledge busy schedule politely: 'Namaste {first_name}, understand you might be occupied.'",
                    "Offer non-intrusive communication: 'Can I share a 1-page rooftop solar estimate here on WhatsApp?'",
                    f"Mention electricity bill reduction potential in {city} (up to 80% savings under PM Surya Ghar).",
                ],
                "suggested_whatsapp_message": (
                    f"Namaste {first_name} ji! I tried reaching you regarding your rooftop solar enquiry in {city}. "
                    "I understand you may be busy right now. Could you please let me know a convenient time to connect, "
                    "or should I share a quick savings breakdown here on WhatsApp?"
                ),
                "objections_to_expect": [
                    {
                        "objection": "I don't have time to talk on calls.",
                        "reply": "No problem at all! I can share all details and savings estimates directly here on WhatsApp for you to review at your convenience."
                    },
                    {
                        "objection": "Is this a promotional spam call?",
                        "reply": "Not at all. You recently filled out our solar enquiry form, and I am following up to assist with your rooftop eligibility and government subsidy."
                    }
                ],
            }, 0

        # Case 2: Price or budget concern
        if latest_outcome == "Price or budget concern" or status == "Interested" and any("price" in str(a.get("notes", "")).lower() for a in recent_activities):
            return {
                "situation_summary": (
                    f"{first_name} has demonstrated interest in solar but expressed reservations about the upfront capital expenditure. "
                    "Clear ROI calculations and central subsidy awareness are critical to unlocking this deal."
                ),
                "risk_level": "medium",
                "risk_reason": "Customer is price-sensitive and may stall without clear payback and EMI numbers.",
                "best_next_action": "Share PM Surya Ghar subsidy breakdown and calculate exact 3-year payback period.",
                "suggested_follow_up_timing": "Tomorrow around 11:30 AM",
                "suggested_outcome_to_log": "Price or budget concern",
                "talking_points": [
                    "Highlight direct central government subsidy: ₹78,000 direct DBT for systems up to 3 kW.",
                    "Present zero-down EMI options where the monthly electricity bill savings exceed the loan installment.",
                    f"Typical payback in {city} is 3.2 to 3.8 years, followed by 20+ years of virtually free power.",
                ],
                "suggested_whatsapp_message": (
                    f"Namaste {first_name} ji! Here is the good news: under the PM Surya Ghar scheme, you are eligible for up to ₹78,000 direct bank subsidy. "
                    f"For a typical {monthly_bill or '₹3,000+'} monthly bill, your solar system pays for itself in less than 3.5 years. "
                    "May I share a 1-page subsidy and EMI calculation sheet?"
                ),
                "objections_to_expect": [
                    {
                        "objection": "Solar is too expensive right now.",
                        "reply": "With the ₹78,000 central subsidy and low-interest green loans (under 7%), your monthly electricity bill savings will actually be higher than your EMI."
                    },
                    {
                        "objection": "How reliable is the government subsidy release?",
                        "reply": "The PM Surya Ghar subsidy is credited directly to your bank account via DBT within 30 days of net-meter commissioning. We handle all paperwork."
                    }
                ],
            }, 0

        # Case 3: Quotation sent and awaiting response / Negotiation
        if status in ["Quote sent", "Negotiation", "Revising quote"] or quotes:
            latest_quote = quotes[-1] if quotes else {}
            kw = latest_quote.get("system_size_kw", 3.3)
            brand = latest_quote.get("brand", "Tier-1")
            net_price = latest_quote.get("net_price", 0)

            return {
                "situation_summary": (
                    f"Quotation v{latest_quote.get('version', 1)} for a {kw} kW system ({brand}) has been presented to {first_name}. "
                    "Customer is likely evaluating economics or comparing with local market proposals."
                ),
                "risk_level": "medium" if status == "Quote sent" else "low",
                "risk_reason": "High-intent stage; delaying follow-up risks losing the customer to a competitor.",
                "best_next_action": "Conduct a consultative quotation walkthrough and address specific equipment or warranty questions.",
                "suggested_follow_up_timing": "Tomorrow between 4:00 PM and 5:30 PM",
                "suggested_outcome_to_log": "Customer compares with another vendor" if status == "Negotiation" else "Customer asks questions",
                "talking_points": [
                    f"Walk through the net investment of ₹{net_price:,.0f} and annual generation guarantee.",
                    f"Highlight Tier-1 equipment advantages: 25-year linear performance warranty on {brand} modules.",
                    "Explain our local maintenance SLA: dedicated service engineer with guaranteed 24-hour breakdown turnaround.",
                ],
                "suggested_whatsapp_message": (
                    f"Namaste {first_name} ji! Hope you had a chance to review the {kw} kW solar proposal we shared. "
                    "I would be glad to do a quick 5-minute call today to answer any questions about panel brands, warranty, or net metering. What time works best?"
                ),
                "objections_to_expect": [
                    {
                        "objection": "Another vendor is offering a lower quote.",
                        "reply": "Check whether their quote uses authentic DCR-certified Mono-PERC modules and branded IP65 inverters. We provide a 25-year performance warranty and 5-year free comprehensive AMC.",
                    },
                    {
                        "objection": "What happens during heavy monsoon or cloudy days?",
                        "reply": "Grid-tied solar systems remain connected to the DISCOM grid. On overcast days, any deficit is automatically supplied by the grid without interruption."
                    }
                ],
            }, 0

        # Case 4: Site Survey Phase
        if status in ["Survey to schedule", "Survey scheduled", "Survey rescheduled", "Survey missed"]:
            return {
                "situation_summary": (
                    f"{first_name}'s lead is in the site inspection phase. "
                    "Verifying rooftop shadow-free area and electrical meter path is the gateway to finalizing the quotation."
                ),
                "risk_level": "medium" if status == "Survey missed" else "low",
                "risk_reason": "Physical site survey conversion rate is high (>65%) once successfully conducted.",
                "best_next_action": "Confirm surveyor arrival window and ask homeowner to keep their latest electricity bill and roof access ready.",
                "suggested_follow_up_timing": "Today within 2 hours",
                "suggested_outcome_to_log": "Survey booked" if status == "Survey to schedule" else "Customer not at site or not reachable on the day",
                "talking_points": [
                    "Survey takes only 20-30 minutes and includes 3D shadow analysis and structural roof health check.",
                    f"Ensure {roof_type} roof access is arranged and recent DISCOM electricity bill copy is accessible.",
                    "Survey engineer will determine the optimal kW capacity to zero out your power bill.",
                ],
                "suggested_whatsapp_message": (
                    f"Namaste {first_name} ji! Our solar technical engineer is preparing for your site inspection in {city}. "
                    "The survey takes just 25 minutes to measure your roof space and check wiring paths. "
                    "Could you please confirm if your roof access will be available?"
                ),
                "objections_to_expect": [
                    {
                        "objection": "Do I have to pay anything for the site survey?",
                        "reply": "Not at all. The site technical inspection and 3D shadow report are completely complimentary with zero commitment required."
                    },
                    {
                        "objection": "Will mounting solar panels damage my RCC roof or cause water leakage?",
                        "reply": "No, we use non-penetrating anchor fasteners with specialized chemical waterproofing sealants, completely safeguarding your roof against leaks."
                    }
                ],
            }, 0

        # Case 5: Design Pending / Technical Feasibility Complete
        if status in ["Design pending", "Alternative"]:
            return {
                "situation_summary": (
                    f"Site survey for {first_name} has concluded. "
                    "The customer is primed for engineering design presentation and financial proposal."
                ),
                "risk_level": "low",
                "risk_reason": "Site technical viability confirmed; speed of quotation delivery dictates close rate.",
                "best_next_action": "Finalize customized 3D solar layout and generate Proposal v1.",
                "suggested_follow_up_timing": "Tomorrow morning by 10:30 AM",
                "suggested_outcome_to_log": "Quote sent, no reply",
                "talking_points": [
                    "Present the exact shadow-free layout tailored to the roof dimensions.",
                    "Demonstrate generation estimates: ~4 units per kW per day in sunny conditions.",
                    "Present clear payment milestones and subsidy paperwork timeline.",
                ],
                "suggested_whatsapp_message": (
                    f"Namaste {first_name} ji! Good news: your site inspection report is ready and your roof is well-suited for solar. "
                    "Our design engineer is preparing your customized proposal with exact 3D panel placement. May I share it with you tomorrow morning?"
                ),
                "objections_to_expect": [
                    {
                        "objection": "Can we install a larger system than our sanction load?",
                        "reply": "DISCOM net-metering regulations typically allow up to 100% of sanctioned load. If required, we assist with sanction load enhancement paperwork."
                    }
                ],
            }, 0

        # Case 6: Nurture / Long-term
        if status == "Nurture":
            return {
                "situation_summary": (
                    f"{first_name} is in the nurture queue ({context.get('nurture_reason', 'waiting for right time')}). "
                    "A non-salesy value check-in keeps our company top-of-mind without causing fatigue."
                ),
                "risk_level": "low",
                "risk_reason": "Dormant lead; requires low-frequency relationship nurturing.",
                "best_next_action": "Send an informative update on solar subsidy deadlines or electricity tariff increases.",
                "suggested_follow_up_timing": "Scheduled follow-up date",
                "suggested_outcome_to_log": "Interested, wants more information",
                "talking_points": [
                    "Highlight recent local electricity tariff revisions in your state.",
                    "Inform customer about active PM Surya Ghar subsidy application window.",
                    "Offer to re-evaluate savings whenever construction or budget permits.",
                ],
                "suggested_whatsapp_message": (
                    f"Namaste {first_name} ji! Just a gentle update: electricity tariffs in {city} have increased recently. "
                    "Whenever you are ready to evaluate solar for your home, our earlier calculations are saved and ready to activate."
                ),
                "objections_to_expect": [
                    {
                        "objection": "We are still not ready to invest.",
                        "reply": "Completely understood! We will keep your file active and follow up whenever the timing is right for you."
                    }
                ],
            }, 0

        # Case 7: Default / New Lead Qualification
        return {
            "situation_summary": (
                f"New lead {first_name} in {city} awaiting initial consultative discovery. "
                f"Recorded property type is {context.get('property_type', 'Residential')} with {roof_type} roof."
            ),
            "risk_level": "low",
            "risk_reason": "Fresh lead; timely first contact within 1 hour yields the highest conversion probability.",
            "best_next_action": "Call customer to verify monthly electricity consumption and decision maker availability.",
            "suggested_follow_up_timing": "Today as soon as possible",
            "suggested_outcome_to_log": "Interested, wants more information",
            "talking_points": [
                f"Greet politely: 'Namaste {first_name}, calling from Solar CRM regarding your rooftop solar inquiry.'",
                f"Confirm monthly electricity bill (approx {monthly_bill or '₹2,500 - ₹5,000'}) and average summer peak.",
                "Confirm rooftop ownership: private independent roof vs. shared apartment terrace.",
                "Propose a free 25-minute technical site survey to assess panel capacity and government subsidy.",
            ],
            "suggested_whatsapp_message": (
                f"Namaste {first_name} ji! Thank you for inquiring about rooftop solar with us in {city}. "
                "With the government's PM Surya Ghar scheme, residential homeowners can save up to 80% on their power bills. "
                "I would love to connect for 3 minutes to share details. What time is good to call?"
            ),
            "objections_to_expect": [
                {
                    "objection": "Just exploring, not ready to buy.",
                    "reply": "That's completely fine! Most of our customers start by checking their roof viability and subsidy eligibility first. We can share a simple brochure to start with."
                },
                {
                    "objection": "Do I need permission from the electricity board?",
                    "reply": "Yes, net-metering approval is required, but our team handles the entire DISCOM application and inspection from start to finish."
                }
            ],
        }, 0


class AnthropicProvider(AISuggestionProvider):
    """
    Concrete Anthropic Messages API Provider using the official `anthropic` SDK.
    Calls Claude 3.5 Sonnet to generate contextual, high-precision solar sales coaching.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key or getattr(settings, 'ANTHROPIC_API_KEY', '')
        self.model = model or getattr(settings, 'AI_MODEL', 'claude-sonnet-5-5')
        self.timeout = timeout or getattr(settings, 'AI_TIMEOUT_SECONDS', 15)

    def generate(self, context: dict[str, Any]) -> tuple[dict[str, Any], int]:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured.")

        import anthropic

        client = anthropic.Anthropic(
            api_key=self.api_key,
            timeout=float(self.timeout),
        )

        lead_summary_json = json.dumps(context, indent=2)
        user_prompt = build_sales_coach_user_prompt(lead_summary_json)

        response = client.messages.create(
            model=self.model,
            max_tokens=1500,
            system=SOLAR_SALES_COACH_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )

        # Extract text content
        raw_text = ""
        for block in response.content:
            if getattr(block, 'type', '') == 'text':
                raw_text += block.text

        tokens_used = (
            getattr(response.usage, 'input_tokens', 0) +
            getattr(response.usage, 'output_tokens', 0)
        )

        # Parse JSON output safely
        parsed_json = self._parse_json_safely(raw_text)
        return parsed_json, tokens_used

    def _parse_json_safely(self, text: str) -> dict[str, Any]:
        """Strips markdown code fences and parses JSON safely."""
        cleaned = text.strip()
        # Strip ```json ... ``` or ``` ... ```
        fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned, re.IGNORECASE)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        try:
            data = json.loads(cleaned)
            if not isinstance(data, dict):
                raise ValueError("Model output did not parse into a dictionary.")

            # Validate mandatory schema keys
            required_keys = [
                "situation_summary",
                "risk_level",
                "best_next_action",
                "talking_points",
                "suggested_whatsapp_message",
            ]
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"Missing required key in AI response: {key}")

            return data
        except Exception as e:
            logger.error(f"Failed to parse Anthropic JSON response: {e}. Raw content: {text[:200]}")
            raise ValueError(f"Invalid JSON returned by AI model: {e}") from e

