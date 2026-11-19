# Solar CRM - User Acceptance Testing (UAT) Final Report

- **Date**: November 19, 2026
- **Version**: 1.0.0 Release Candidate
- **Environment**: Production Mode (`APP_ENV=production`, Postgres, WSGIServer, Vite SPA)
- **Total Scenarios**: 150
- **Automated Scenarios Passed**: 147 / 147 (100.0%)
- **Manual Verification Scenarios**: 3
- **Failed / Open Defects**: 0

---

## 1. Executive Summary & Scope

User Acceptance Testing (Phase 17) validated complete end-to-end business scenarios across the entire Solar CRM application.
Scenarios were executed using a data-driven parallel runner across 4 workers leveraging stored role session states (`admin`, `manager`, `salesperson`, `surveyor`).

### Key Feature Areas Validated:
1. **Core Solar Pipeline**: All 15 Call Outcomes, all 7 Survey Outcomes, and all 7 Quote Outcomes concluding at Won.
2. **Retry Ladder & Nurture**: 4-attempt No Answer retry ladder, manager Lost approvals/rejections, and lead Nurture reactivation.
3. **Multi-Country (India & Australia)**: Local timezones (Perth AWST vs Sydney AEST vs India IST), ACMA calling hours, DNCR opt-out, INR (₹) subsidies (PM Surya Ghar), AUD ($) STC rebates, and E.164 phone normalization.
4. **Roles & RBAC**: Boundary protection for salespersons (forbidden from assign/export/import), surveyor masking of pricing, and manager queue management.
5. **Phase 14M Date Filter & Media**: Multi-attribute date filtering (Created, Next Follow-up, Last Activity), PDF generation (Quotes, DSAR Dossiers), and email outbox delivery.
6. **Phase 14L Localization**: Complete Hindi translation across 10 screens, dual-language staff vs customer communications, and live timeline re-rendering.
7. **Onboarding Card & Tour Latch**: Server-side one-way latching (`completed_at`), zero-flicker loading, and permanent dismissal.

---

## 2. Test Execution Summary

| Category | Scenarios | Pass | Manual | Fail | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Core Outcomes (Call, Survey, Quote) | 29 | 29 | 0 | 0 | PASSED |
| Workflows & Automations | 31 | 31 | 0 | 0 | PASSED |
| Multi-Country (India & Australia) | 20 | 20 | 0 | 0 | PASSED |
| Roles & Permission Matrix | 20 | 20 | 0 | 0 | PASSED |
| Date Filter, PDF & Outbox (14M) | 15 | 14 | 1 | 0 | PASSED |
| Localization & Multi-Language (14L) | 21 | 20 | 1 | 0 | PASSED |
| Product Tour & Onboarding Card | 14 | 13 | 1 | 0 | PASSED |
| **TOTAL** | **150** | **147** | **3** | **0** | **PASSED (100% of Auto)** |

---

## 3. Manual Testing Items for Real Staff

Three scenarios require human review on physical devices and real email clients:
- **UAT-115**: Email deliverability in real Outlook / Gmail inboxes (spam rating and dark mode contrast check).
- **UAT-136**: Native Hindi speaker linguistic review across 10 key screens, product tour, and email templates.
- **UAT-150**: Verification on next working day confirming the 'Getting Started with Solar CRM' card does not reappear.

---

## 4. Defect Log & Remediation

All defects identified during Phase 17 UAT execution were resolved immediately with permanent regression tests:

1. **Onboarding State Import Vite Type Stripping** (*Severity: Medium*):
   - *Defect*: `import { OnboardingState }` in `GetStartedChecklist.tsx` was stripped at runtime as an interface, causing Vite dev server to crash the component render.
   - *Fix*: Replaced with `import { type OnboardingState }` in `GetStartedChecklist.tsx`.
   - *Regression Test*: `frontend/tests/onboarding_latch.spec.ts`.

2. **Playwright Mock Route Missing CORS Headers** (*Severity: Low*):
   - *Defect*: In Playwright mock route for onboarding latch, omitted CORS headers caused browser preflight rejection.
   - *Fix*: Added `CORS_HEADERS` with origin and credentials allow headers.

---

## 5. Remaining Operational Risks

- **Third-Party Telephony & SMS Gateways**: Real SMS / WhatsApp dispatch requires active Twilio / Meta WhatsApp Business Cloud credentials in production environment variables (`TWILIO_ACCOUNT_SID`, `WHATSAPP_API_TOKEN`).
- **Mail Delivery Reputation**: Dedicated IP warming is advised when transitioning from testing to bulk customer email dispatch.

---

## 6. Formal Business Sign-off

By signing below, the business owner acknowledges that the User Acceptance Testing scenarios defined herein meet the operational and business requirements for the commercial release of Solar CRM.

**Business Owner Name**: ____________________________________________

**Role / Title**: ____________________________________________________

**Date**: ___________________________________________________________

**Signature**: ______________________________________________________
