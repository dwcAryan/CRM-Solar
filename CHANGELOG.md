# Changelog

All notable changes to the Solar CRM platform are documented in this file.

## [1.0.0] - 2026-11-19

### Phase 18: User Manual (PDF in EN & HI) and Production Release
- **User & Operations Manual**: Compiled professional 23-page PDF manual (`Solar_CRM_User_Manual_v1.0.pdf`) and 16-page Hindi edition (`Solar_CRM_User_Manual_v1.0_hi.pdf`) using Playwright PDF rendering engine.
- **Automated Quality Audit**: Verified zero blank pages, page text density, image embeds, and strict file size constraint (< 15 MB).
- **In-App Manual Access**: Added authenticated User Manual PDF endpoint (`/api/docs/manual/`), Help menu navigation link, About Solar CRM modal, and Helpbot knowledge articles.
- **Production Package**: Built release archive `dist/solar-crm-v1.0.zip` from strict allowlist with SHA-256 checksum and comprehensive `GO_LIVE_CHECKLIST.md`.

### Phase 17: User Acceptance Testing (UAT)
- **Comprehensive Scenarios**: Executed 150 end-to-end business scenarios (147 automated passed in 306.5s, 3 manual verification items).
- **Server-Side Onboarding Latch**: Implemented `UserOnboardingState` latch with zero-flicker loading, 3-second celebration transition, and permanent dismissal across reloads, logouts, and viewport changes.
- **Reporting & Artifacts**: Delivered `UAT_REPORT.md`, formatted `UAT_TRACKER.xlsx`, printable `UAT_CHECKLISTS.md`, and 147 evidence screenshots.

### Phase 16: Full Regression Testing & Continuous Verification
- **Regression Matrix**: Created `docs/REGRESSION_MATRIX.md` mapping 100% of functional requirements to automated suites.
- **Multi-Layer Validation**: 193 pytest scenarios passed (including 116 security & permission checks), 126 Vitest unit tests passed with 94.8% branch coverage, and Playwright suites verified on desktop and 390px mobile.

### Phase 15: Security Hardening & Penetration Testing
- **Automated Static Scanning**: Cleared SAST across Bandit, pip-audit, npm audit, semgrep, and detect-secrets with zero high/critical vulnerabilities.
- **Dynamic Penetration Testing**: Verified IDOR isolation across regions/roles, formula injection prevention in CSV exports, JWT refresh token revocation on logout, host header spoofing immunity, and strict CSP / Permissions-Policy headers.
- **API Fuzzing**: Schemathesis contract fuzzing across 195 endpoints (409 generated test cases) yielding 0 unhandled exceptions or data leaks.

### Phase 14M: Date Range Filtering, PDF & Email Engine Audit
- **Lead Date Range Filter**: Multi-attribute date filtering (Created, Next Follow-up, Last Activity, Last Updated, Won Date) with Mantine date pickers, quick presets (Today, Last 7 days, This Month), removable chips, and URL query synchronization.
- **PDF Engine Hardening**: XML escaping for ReportLab flowables, dynamic currency formatting, and pagination.
- **Email Service Audit**: Added preference checks, DNC opt-out enforcement, template rendering tests, and interactive `check_email` command.

### Phase 14L: Multi-Language Support & Localization (English & Hindi)
- **Dual-Language Architecture**: Strict decoupling of staff interface language (`User.preferred_language`) and customer communication language (`Lead.preferred_language`).
- **Data-Driven Extensibility**: 5-step data-only workflow for adding new languages without code deployment.
- **System-Wide Translations**: Complete Hindi translation covering 10 screens, navigation, modals, product tour, Helpbot articles, and master data with dynamic read-time audit rendering.

### Phase 14: Cleanup, Demo Autofill Removal, and Production Mode
- **Removed Demo Autofills**: Stripped all pre-filled credentials, 1-click login buttons, and role shortcuts from `LoginPage.tsx`.
- **Forced Password Change**: Implemented `must_change_password` flag and required password change modal on first login for provisioned accounts.
- **Admin Setup**: Added interactive `create_admin` management command enforcing $\ge 10$ char password complexity with upper, lower, number, and special character rules.
- **Demo Management**: Scoped `seed_demo` to UAT/training only (refuses to run under `APP_ENV=production`), prefixing accounts with `demo_` and marking `is_demo=True`. Added `remove_demo_data` command with atomic cascade deletion and interactive confirmation.
- **Production Mode**: Enabled `python run.py --prod` with Whitenoise compressed manifest static serving, Waitress (Windows) / Gunicorn (Unix) WSGI servers, health check at `/api/health/`, and structured log rotation with `SensitiveDataFilter`.
- **Repository Clean**: Purged old database dumps, scratch files, and unused assets.

### Phase 13: Product Tour and AI Help Assistant
- Built role-aware Product Tour with Shepherd.js / Mantine drawer and step spotlights.
- Built intelligent Helpbot with hybrid local TF-IDF / BM25 NLP retrieval and optional Anthropic fallback.
- Added Helpbot Analytics and knowledge coverage telemetry in Admin portal.

### Phase 12: Email (SMTP) Integration
- Unified email dispatch service supporting Google Workspace, Zoho, Brevo, SES, and Outlook.
- Automated daily morning follow-up digests and survey reminders.
- Implemented `EmailLog` audit tracking with credentials scrubbing.

### Phase 11: Desktop PWA and Web Push Notifications
- Configured progressive web app (PWA) with offline fallback and standalone display.
- Added bottom sidebar "Download for desktop" installation prompt.
- Added Web Push notifications via VAPID with quiet hours enforcement.

### Phase 10: Unified Runner and Demo Infrastructure
- Created zero-dependency cross-platform runner script `run.py`.
- Automated PostgreSQL readiness checks, venv setup, and requirement hashing.

### Phase 9: Strict Role-Based Access Control (RBAC)
- Enforced role matrix across `admin`, `manager`, `salesperson`, and `surveyor`.
- Restrained data access so salespersons and surveyors only see their assigned leads in permitted regions.

### Phase 8: Multi-Country Support (India & Australia)
- Integrated localized currency isolation (`INR` vs `AUD`), postal validation (PIN vs Postcode), and state/retailer masters.
- Added localized legal opt-out notices and calling hours restriction engine.

### Phases 1-7: Core Solar CRM Engine
- Lead pipeline, outcome-driven activity logging, quotes, rooftop survey management, and AI suggestions.
