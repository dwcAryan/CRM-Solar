---
topic: lost_rules
title: Lost Leads Rules and Approvals
keywords: lost lead, lost reason, mark lost, who can mark lost, competitor, rejection, drop lead
roles: [admin, manager, salesperson]
regions: [IN, AU]
---
# Lost Leads Rules and Permissions

Marking a solar lead as "Lost" closes the pipeline opportunity. Strict rules govern how and when a lead can be marked Lost.

## Required Fields for Lost Status
When marking a lead as Lost, the user MUST provide:
1. **Lost Reason**: Standard category (e.g., "Competitor Price Cheaper", "Roof Unsuitable / Shading", "Tenant / No Roof Rights", "Financial Constraint", "Not Interested").
2. **Competitor Name**: If lost to a rival solar installer, the competitor name must be specified.
3. **Detailed Remarks**: Explanation of why the opportunity could not be saved.

## Authority and Permission Controls
- In Policy Settings, `who_can_mark_lost` controls whether Salespeople can directly mark leads as Lost, or if it requires Manager / Admin approval.
- By default, Salespeople can submit a "Request Mark Lost", which Managers review, preventing accidental or premature lead abandonment.
- Managers and Admins have full authority to mark leads as Lost immediately.
