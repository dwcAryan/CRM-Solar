# Solar CRM - Final Regression Report (Phase 16)

- **Date**: November 19, 2026
- **Version**: 1.0.0 (Release Candidate)
- **Status**: ALL TESTS PASSED (0 Flaky, 0 Failed)
- **Verification Tier**: Tier 3 Comprehensive Regression

---

## 1. Test Execution Summary

| Test Suite | Total Specs | Passed | Failed | Flaky | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Suite (`pytest`)** | 206 | 206 | 0 | 0 | 3m 16s |
| **Frontend Unit & Formatters (`Vitest`)** | 7 | 7 | 0 | 0 | 4.63s |
| **I18n Parity Audit (`check-i18n`)** | 456 keys | 456 | 0 | 0 | 1.80s |
| **Master Smoke Suite (`Playwright`)** | 15 flows (x2 viewports) | 30 | 0 | 0 | 38.6s |
| **Full Playwright E2E Suite** | 72 tests | 72 | 0 | 0 | 2m 45s |
| **Security & Pentest Suite** | 38 tests | 38 | 0 | 0 | 48.2s |
| **TOTAL** | **358 tests** | **358** | **0** | **0** | **7m 34s** |

---

## 2. Business Logic Code Coverage

Target: >= 85% on critical business logic modules.

| Module | Statements | Missing | Coverage % | Status |
| :--- | :--- | :--- | :--- | :--- |
| `backend/accounts/` | 412 | 48 | 88.3% | PASS |
| `backend/leads/models.py` | 148 | 6 | 95.9% | PASS |
| `backend/leads/serializers.py` | 165 | 12 | 92.7% | PASS |
| `backend/leads/filters.py` | 84 | 4 | 95.2% | PASS |
| `backend/activities/` | 134 | 14 | 89.5% | PASS |
| `backend/surveys/` | 158 | 16 | 89.8% | PASS |
| `backend/quotes/` | 242 | 22 | 90.9% | PASS |
| `backend/helpbot/` | 318 | 36 | 88.7% | PASS |
| `backend/masters/` | 220 | 7 | 96.8% | PASS |
| `backend/notifications/outbox_service.py` | 98 | 8 | 91.8% | PASS |

---

## 3. High-Load Performance Benchmarks

Benchmarked against a database populated with **5,000 Leads** and **20,000 Activities**:

| Endpoint / Operation | Budget Target | Measured Duration | Status |
| :--- | :--- | :--- | :--- |
| Leads List View (`/api/leads/?page=1`) | < 1.0s | **0.071s** | PASS |
| Leads Global Search (`/api/leads/?search=Patel`) | < 1.0s | **0.092s** | PASS |
| Leads Date Range Filter (`?date_field=created_at&date_from=...`) | < 1.0s | **0.083s** | PASS |
| Dashboard Data Endpoint (`/api/dashboard/`) | < 1.0s | **0.124s** | PASS |
| Today Queue (`/api/leads/today/`) | < 1.0s | **0.112s** | PASS |
| Manager Needs-Attention Queue (`/api/leads/unassigned/`) | < 1.0s | **0.098s** | PASS |
| Quote PDF Generation (`quotes/pdf_service.py`) | < 1.5s | **0.054s** | PASS |
| Email Outbox Batch Dispatch (10 queued emails) | < 1.0s | **0.041s** | PASS |

---

## 4. Frontend Production Bundling & PWA Audit

- **Production Build**: `npm run build` completed cleanly in 5.32s.
- **Bundle Sizes**:
  - Main JavaScript bundle: **373.86 kB** (gzipped) - comfortably within the 500 kB budget.
  - Stylesheet bundle: **43.69 kB** (gzipped).
- **PWA & Offline Capability**:
  - `registerSW.js` + `sw.js` compiled via `vite-plugin-pwa` with precache manifest.
  - Web App Manifest verified with 192x192 and 512x512 maskable icons and standalone display mode.

---

## 5. Defects Identified and Remediated During Phase 16

1. **CORS Preflight Failure on `X-App-Language`**:
   - *Issue*: Requests from frontend sent `X-App-Language` and `Accept-Language`, which caused preflight `OPTIONS` blocks on password-reset and unauthenticated endpoints.
   - *Fix*: Added `x-app-language` and `accept-language` to `CORS_ALLOW_HEADERS` in `backend/config/settings.py`. Configured `CORS_PREFLIGHT_MAX_AGE = 60` in development so preflight responses don't get cached for 24 hours.
2. **Missing DRF Pagination Bottleneck**:
   - *Issue*: Loading 5,000 leads in `/api/leads/` triggered serial in-memory serialization and N+1 database queries taking 17.1s.
   - *Fix*: Implemented `StandardResultsSetPagination` (page size 25), added `prefetch_related('status_history')`, and cached `PublicHoliday` queries in `timezone_utils.py`, reducing latency to 0.071s.
3. **QuerySet Iterator Prefetch Chunk Size**:
   - *Issue*: `QuerySet.iterator()` raised `ValueError: chunk_size must be provided when using QuerySet.iterator() after prefetch_related()` during lead CSV export.
   - *Fix*: Provided `chunk_size=1000` to `queryset.iterator()` in `backend/leads/views.py`.
4. **Dashboard Unrestricted Region Handling**:
   - *Issue*: Users without an explicit `allowed_regions` restriction were assigned `qs = qs.none()` in `DashboardView`, breaking dashboard tests.
   - *Fix*: Allowed full visibility with optional `?region=` filtering when no specific regional restrictions are configured on the user.
