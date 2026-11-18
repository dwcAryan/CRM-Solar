---
topic: ai_suggestions
title: AI Suggestions on Lead Detail Page
keywords: ai suggestions, lead advice, next step recommendation, anthropic, rules fallback, lead insights
roles: [admin, manager, salesperson]
regions: [IN, AU]
---
# AI Suggestions on Lead Details

On every lead's detail page, the **AI Suggestions** panel analyzes the lead's entire history, stage, notes, call attempts, and bill size to provide intelligent action recommendations.

## How It Operates
1. **Context Analysis**: Evaluates customer property type, monthly power consumption, previous call outcomes, customer objections, and days since last contact.
2. **Actionable Recommendations**:
   - Suggests optimal calling windows or alternative channels (e.g. WhatsApp message if 3 phone calls went unanswered).
   - Recommends subsidy calculations when a customer expresses price sensitivity.
   - Highlights warranty and service differentiators when a customer is comparing competitors.
3. **Dual Engine (Zero Key Dependency)**:
   - If an Anthropic API key is configured, it uses Claude Sonnet to generate tailored conversational strategies.
   - If no key is set or `AI_PROVIDER=rules`, it seamlessly falls back to a deterministic, expert-crafted rule engine with 100% reliability.
