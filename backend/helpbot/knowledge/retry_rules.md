---
topic: retry_rules
title: Automated Retry Ladder and Unreachable Limits
keywords: retry ladder, retry interval, call attempts, busy, no answer, switched off, unreachable, retry schedule, ladder
roles: [admin, manager, salesperson]
regions: [IN, AU]
---
# Automated Retry Ladder and Unreachable Rules

When a customer cannot be reached (outcomes: Busy, No Answer, Switched Off), the CRM calculates the next retry time based on the Retry Ladder policy.

## Retry Intervals (Default Policy)
- **1st Failed Attempt**: Retry in 1 hour (if within business hours) or next morning at opening time.
- **2nd Failed Attempt**: Retry in 3 hours.
- **3rd Failed Attempt**: Retry in 6 hours or switch communication channel (e.g., automated WhatsApp or SMS template asking when to call).
- **4th Failed Attempt**: Retry on the next business day at an alternate time slot (morning if prior calls were afternoon).

## Maximum Call Attempts
- The system tracks `call_attempts_count` on every lead.
- The default threshold is configured in **Policy Settings** (typically 5 to 7 attempts).
- Once the maximum call attempts threshold is reached without connection, the CRM automatically marks the lead as **Unreachable / Cold**.
- Salespeople cannot arbitrarily mark active leads unreachable without exhausting the required call attempt steps.
