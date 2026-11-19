# Solar CRM - Full Regression Matrix (Phase 16)

Date: November 19, 2026  
Version: 1.0.0 (Release Candidate)  
Verification Tier: Tier 3 Full Verification

---

## 1. Regression Test Mapping

| Feature Area | Sub-feature / Requirement | Test Suite | Test File | Test Identifiers / Spec | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Authentication & RBAC** | Admin, Manager, Salesperson, Surveyor roles | Playwright | `frontend/tests/smoke_suite.spec.ts` | `02. Login as admin`, `03. Manager`, `04. Salesperson`, `05. Surveyor` | PASS |
| | Clean login without hardcoded demo buttons | Playwright | `frontend/tests/login_clean.spec.ts` | `login page has empty inputs, standard placeholders` | PASS |
| | Granular Permission Matrix across all roles | pytest | `backend/tests/test_permission_matrix.py` | `TestPermissionMatrix::test_matrix_compliance` | PASS |
| | Password Reset (token expiration, CORS, rate limits) | Playwright / pytest | `frontend/tests/smoke_suite.spec.ts`, `backend/tests/security/test_security_suite.py` | `06. Forgot-password flow trigger`, `test_password_reset_flow` | PASS |
| | Must change password enforcement | pytest | `backend/tests/security/test_security_suite.py` | `test_must_change_password_enforced` | PASS |
| **Leads Management** | Lead creation & validations | pytest / Playwright | `backend/tests/test_phase3_business_logic.py`, `frontend/tests/smoke_suite.spec.ts` | `test_create_lead`, `07. Create lead flow` | PASS |
| | Lead search & query filters | pytest | `backend/tests/test_phase16_performance.py` | `test_lead_list_and_search_under_1_second` | PASS |
| | From-Date and To-Date Filters (Phase 14M) | Playwright / pytest | `frontend/tests/leads_date_filter.spec.ts`, `backend/tests/test_phase14m_date_filter.py` | `desktop: select preset, active chip, clear filter`, `test_lead_date_filter_presets` | PASS |
| | Bulk actions & CSV export | pytest | `backend/tests/test_phase14m_date_filter.py`, `backend/tests/test_phase6_csv_remarks_and_features.py` | `test_export_and_bulk_action_honoring_date_filter`, `test_export_leads_csv_with_formula_escaping` | PASS |
| | Duplicate detection and merge | pytest | `backend/tests/test_phase3_business_logic.py` | `test_duplicate_phone_detection`, `test_lead_merge` | PASS |
| **Outcomes & Workflow** | Call outcomes & next-followup rule | pytest / Playwright | `backend/tests/test_phase3_business_logic.py`, `frontend/tests/smoke_suite.spec.ts` | `test_call_outcome_schedule`, `09. Log call outcome flow` | PASS |
| | Retry ladder (No answer -> Unreachable -> Lost) | pytest | `backend/tests/test_phase3_business_logic.py` | `test_retry_ladder_unreachable_to_lost` | PASS |
| | Lost approval workflow by Manager | pytest | `backend/tests/test_phase3_business_logic.py` | `test_lost_approval_pending_manager_approve` | PASS |
| | Do Not Contact (DNC) blocking | pytest | `backend/tests/test_phase4_reminders_and_messaging.py` | `test_dnc_blocks_messaging_and_calls` | PASS |
| | Remarks mandatory on workflow steps | pytest | `backend/tests/test_phase6_csv_remarks_and_features.py` | `test_remarks_mandatory_on_status_change` | PASS |
| **Surveys** | Book, reschedule, missed, cancel, done | pytest / Playwright | `backend/tests/test_phase3_business_logic.py`, `frontend/tests/smoke_suite.spec.ts` | `test_survey_lifecycle`, `10. Book survey flow` | PASS |
| | Surveyor assignment & role filtering | Playwright | `frontend/tests/rbac_roles.spec.ts` | `Surveyor restricted from leads list and quotes` | PASS |
| **Quotes** | Versioning, revise, accept to Won, reject | pytest / Playwright | `backend/tests/test_phase3_business_logic.py`, `frontend/tests/smoke_suite.spec.ts` | `test_quote_lifecycle_to_won`, `11. Quote to Won flow` | PASS |
| | Multi-currency (INR vs AUD) totals & subsidies | pytest | `backend/tests/test_phase8_multi_country.py` | `test_quote_currency_and_subsidy_calculation` | PASS |
| | PDF quote generation & download | pytest / Vitest / Playwright | `backend/tests/test_phase14m_pdf_audit.py`, `frontend/src/test/downloadPdf.test.ts`, `frontend/tests/pdf_downloads.spec.ts` | `test_quote_pdf_structure_and_assets`, `downloadPdfBlob`, `quotes page: download quote PDF` | PASS |
| **Data Import/Export** | CSV import (valid rows, invalid rows, duplicates, undo) | pytest / Playwright | `backend/tests/test_phase6_csv_remarks_and_features.py`, `frontend/tests/smoke_suite.spec.ts` | `test_csv_import_and_revert_batch`, `13. CSV import leads view` | PASS |
| | Formula escaping on export | pytest | `backend/tests/test_phase6_csv_remarks_and_features.py` | `test_export_leads_csv_with_formula_escaping` | PASS |
| **Dashboards & Queues** | Role dashboards (Admin, Manager, Sales, Surveyor) | pytest | `backend/tests/test_phase16_performance.py` | `test_dashboard_roles_under_1_second` | PASS |
| | Today list & Manager Needs-Attention Queue | pytest | `backend/tests/test_phase7_ai_suggestions.py`, `backend/tests/test_phase16_performance.py` | `test_dashboard_needs_attention`, `test_today_and_manager_queues_under_1_second` | PASS |
| **Notifications & Email** | In-app, push, browser notifications & dialogs | Playwright | `frontend/tests/pwa_and_notifications.spec.ts` | `permission modal appears`, `service worker registers` | PASS |
| | Email outbox, rate limiting, and CSS inlining | pytest | `backend/tests/test_phase14m_email_audit.py` | `test_email_outbox_queue_and_batch_dispatch`, `test_email_premailer_inlines_css` | PASS |
| | DNC opt-out & deliverability validation | pytest | `backend/tests/test_phase12_email.py` | `test_email_opt_out_respected`, `test_check_email_diagnostics` | PASS |
| **AI Suggestions & Helpbot** | Mocked LLM, caching, privacy filter, rate limit | pytest | `backend/tests/test_phase7_ai_suggestions.py` | `test_ai_suggestions_get_and_post_endpoints`, `TestPrivacyFilter` | PASS |
| | Helpbot Assistant (in-scope answers, refusals, feedback) | Playwright / pytest | `frontend/tests/helpbot.spec.ts`, `backend/tests/test_phase13_helpbot.py` | `Helpbot chat interactions, scope refusal, and feedback` | PASS |
| | NLP Intent Classification & Multi-language eval | pytest | `backend/helpbot/tests/test_eval.py` | `test_helpbot_nlu_accuracy_and_scope` | PASS |
| **Desktop & PWA** | Web app manifest, service worker, installability | Playwright | `frontend/tests/pwa_and_notifications.spec.ts` | `manifest is served and valid with icons`, `service worker registers` | PASS |
| | Product Tour & Checklist | Playwright | `frontend/tests/product_tour.spec.ts` | `Tour targets and Tour Center drawer` | PASS |
| **Multi-Language (14L)** | Language selector & resolution (user setting, headers) | Playwright / pytest | `frontend/tests/language_option.spec.ts`, `backend/tests/test_phase14l_i18n.py` | `login page has language selector`, `test_i18n_middleware_resolution` | PASS |
| | Key parity & translation linting | Vitest / Node script | `frontend/scripts/check-i18n.js` | `npm run i18n:check` (456 keys across 12 namespaces) | PASS |
| | Number, date, currency formatting per locale | Vitest | `frontend/src/test/formatters.test.ts` | `formats dates in Hindi and English`, `formats INR and AUD currency` | PASS |
| | Pseudo-locale (`en-XA`) and Pseudo-RTL (`ar-XB`) | Playwright | `frontend/tests/language_option.spec.ts` | `pseudo-RTL locale activates dir="rtl"`, `pseudo-locale expands text length` | PASS |
| | CORS preflight header allow (`x-app-language`) | pytest / curl | `backend/tests/test_phase14l_i18n.py` | `test_cors_preflight_x_app_language_allowed` | PASS |
| **Regions (IN & AU)** | Region-based access control and phone handling | pytest / Playwright | `backend/tests/test_phase8_multi_country.py`, `frontend/tests/smoke_suite.spec.ts` | `test_region_scoping_lead_access`, `14. Region switch IN to AU` | PASS |
| | Calling hours & daylight-saving timezones | pytest | `backend/tests/test_phase8_multi_country.py` | `test_calling_hours_compliance_per_region` | PASS |
| **Data Integrity & Ops** | Database seed and clean cycle | CLI | `python manage.py seed_demo --accounts-only` | `seed_demo` and `remove_demo_data --force` verified | PASS |
| | Backup and restore verification | CLI | `scripts/backup_db.py`, `scripts/restore_db.py` | SQLite/Postgres dump and restore integrity confirmed | PASS |
| | Production build verification | Vite / DRF | `npm run build`, `python run.py --prod` | Static bundle generated, PWA manifest, secret checks | PASS |
| | Performance under 5,000 leads & 20,000 activities | pytest | `backend/tests/test_phase16_performance.py` | All 7 benchmarks < 1.0s (list 0.07s, search 0.09s, PDF 0.05s) | PASS |
