# Changelog

All notable changes to the Solar CRM platform are documented in this file.

## [1.0.0] - 2026-11-18

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
