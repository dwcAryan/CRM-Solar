---
topic: call_outcomes
title: Call Outcomes and Status Transitions
keywords: call outcome, connected, busy, switched off, no answer, wrong number, not interested, callback, status transition
roles: [admin, manager, salesperson]
regions: [IN, AU]
---
# Call Outcomes and Status Transitions

When logging an interaction with a lead, you select one of the standardized Call Outcomes. Each outcome determines the lead's next workflow step.

## Standard Call Outcomes
1. **Connected / Conversation Held**: The customer answered and engaged in conversation. Status moves to "Contacted" or remains active. Next action must be planned.
2. **Callback Requested**: Customer asked to speak later. You must specify a callback date and time. CRM sets a high-priority reminder task.
3. **Busy**: Phone line was busy or rejected. Triggers the automated retry ladder for retry after an interval (e.g. 1 hour).
4. **No Answer / Ringing Unanswered**: The phone rang with no answer. Triggers retry ladder interval (e.g. 3 hours).
5. **Switched Off / Out of Coverage**: Customer's phone was unreachable. Retry scheduled for next business window (e.g. 6 hours).
6. **Wrong Number / Invalid Contact**: Number belongs to someone else or is invalid. Status moves to "Invalid Contact".
7. **Not Interested**: Customer explicitly refused solar interest. Can be marked "Lost" with reason "Not interested in solar".
8. **Site Survey Requested**: Customer agreed to a technical rooftop evaluation. Moves status to "Survey Scheduled".
9. **Quote / Proposal Requested**: Customer requested pricing proposal. Moves status to "Quote Requested".
10. **Follow-up Scheduled**: General follow-up planned.
11. **Deal Won / Converted**: Customer agreed and signed solar contract.
