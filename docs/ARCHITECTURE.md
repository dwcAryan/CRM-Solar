# Solar CRM Architecture & Multi-Country System Specification

## 1. Overview & Golden Rule

Solar CRM is a specialized operational sales system for residential and commercial solar installations in **India (IN)** and **Australia (AU)**.

### The Golden Business Rule
Every interaction (phone call, WhatsApp message, SMS, site visit) must terminate with a logged outcome that sets:
1. **Lead Status**: Defined exclusively by the Outcome Matrix (`masters.Outcome`).
2. **Next Action**: Prescribed by the outcome default or custom sales override.
3. **Next Follow-up Date/Time**: Mandatory unless the status is terminal (`Won`, `Lost`, `Do not contact`, `Merged`, `Invalid contact`).

---

## 2. Multi-Country Data Architecture

### 2.1 Region & Geography Models (`masters`)
- **`Region` Model**:
  - `code`: ISO 3166-1 alpha-2 primary key (`IN`, `AU`).
  - `name`: Display name (`India`, `Australia`).
  - `currency`: ISO code (`INR`, `AUD`).
  - `currency_symbol`: `₹` vs `A$`.
  - `phone_country_code`: `+91` vs `+61`.
  - `tax_label`: `GST`.
  - `tax_rate`: Configurable decimal fraction (e.g. `0.0500` for 5%, `0.1000` for 10%).
  - `incentive_label`: "Subsidy (PM Surya Ghar)" vs "Government incentive (STCs and rebates)".
  - `electricity_provider_label`: "DISCOM" vs "Electricity retailer".
  - `preferred_channels`: JSON list or comma-separated string prioritizing outreach (`['whatsapp', 'call', 'sms']` for IN; `['sms', 'call', 'whatsapp']` for AU).
  - `calling_hours`: JSON dict defining daily windows and restrictions.
  - `opt_out_line`: Default unsubscribe text required on commercial electronic messages.

- **`State` Model**:
  - Code, name, region FK, default timezone, and local clean energy regulator notes.

- **`PublicHoliday` Model**:
  - Date, name, region FK. Calling hours engine checks this list to enforce outbound restrictions on public holidays.

### 2.2 User Access Scoping (`accounts`)
- Custom `User` model (`AbstractUser`) contains:
  - `role`: `admin`, `manager`, `salesperson`, `surveyor`.
  - `allowed_regions`: Many-to-Many relation with `Region`.
  - `default_region`: ForeignKey to `Region`.
  - `default_timezone`: IANA timezone string (`Asia/Kolkata`, `Australia/Sydney`, etc.).
- **Scoping Enforcement**:
  - Salespersons and surveyors only see leads in their assigned `allowed_regions` (and salespersons only see their own assigned leads).
  - Managers and admins with access to multiple regions can toggle views dynamically using the frontend region switcher (`?region=IN`, `?region=AU`, or `ALL`).

### 2.3 Strict Currency Isolation
- **Rule**: Currencies (`INR` and `AUD`) are NEVER mixed, compared, or summed into a single figure.
- Dashboard endpoints return distinct objects:
  ```json
  "won_value_by_currency": {
    "INR": 1850000.0,
    "AUD": 245000.0
  }
  ```
- Quotations snapshot regional currency and symbols at creation time to prevent historical corruption.

---

## 3. Compliance & Regulatory Engines

### 3.1 Calling Hours & Timezone Evaluation (`backend/leads/timezone_utils.py`)
- Outbound outreach is validated against the lead's local timezone.
- **Australia**:
  - Monday–Friday: 09:00 to 20:00.
  - Saturday: 09:00 to 17:00.
  - Sundays & Public Holidays: Strictly blocked.
- **India**:
  - Daily: 09:00 to 20:00.
- When an outreach is attempted outside permitted hours:
  - If calling policy is set to "warn", an explicit override reason must be supplied by the user.
  - The override reason, user, lead, and local timestamp are recorded to the tamper-evident `AuditLog`.

### 3.2 Channel Opt-Outs & Do Not Call Register (DNCR)
- Individual lead opt-out flags:
  - `opt_out_calls`: Hard blocks call logging without explicit override.
  - `opt_out_sms`: Suppresses outbound SMS notifications.
  - `opt_out_whatsapp`: Suppresses automated or template WhatsApp messaging.
  - `opt_out_email`: Suppresses promotional or follow-up emails.
  - `do_not_contact`: Complete global suppression.
- `dncr_status`:
  - `verified_clean`, `listed`, `unverified`.
  - Visual warning pills displayed on lead detail and outcome logging modals.

### 3.3 Privacy & Data Governance Service (`backend/leads/privacy_service.py`)
Compliant with India's DPDP Act 2023 and Australia's Privacy Act 1988:
1. **DSAR Export (Right to Access)**:
   - Generates comprehensive dossiers in JSON or official multi-page PDF via ReportLab.
   - Includes profile, timeline, survey reports, quote versions, and audit history.
2. **Irreversible Anonymization (Right to Erasure / Forgotten)**:
   - Sets lead name to `ANONYMIZED_LEAD_<id>`.
   - Zeros phone, email, address, notes, and remarks.
   - Retains anonymized aggregate quote and survey figures for financial reporting.
   - Logs an immutable entry in `AuditLog`.
3. **Data Rectification (Right to Correction)**:
   - Validates and updates contact details while recording a before/after diff in `AuditLog`.

### 3.4 Tamper-Evident `AuditLog`
- Stored in `leads_auditlog`.
- Overridden `.save()` and `.delete()` methods raise `ValueError` on attempted updates or deletions.
- Records user, action (`calling_hours_override`, `privacy_anonymize`, `privacy_rectify`, `csv_import`, `lead_merge`), reason, and structured JSON details.

---

## 4. Frontend Regional Adaptations

- **`RegionContext`**:
  - Manages `selectedRegion` (`IN`, `AU`, or `ALL`).
  - Provides `currencySymbol`, `formatMoney`, and localized date formatting.
- **Header Selector**:
  - Allows seamless switching between Indian and Australian market contexts.
- **Dynamic Forms**:
  - Adapts address inputs: Indian Pincode (6 digits) vs Australian Suburb + Postcode (4 digits).
  - Adapts billing inputs: Monthly bill vs Quarterly/Two-monthly bill with automatic monthly normalization.
  - Adapts quote inputs: Panel capacity, battery storage (`battery_kwh`), and regional tax explanation.
- **Calling Hours Badges**:
  - Displays live local customer time and calling status (e.g. `● Calling Hours: Open (14:35 AEDT)` or `⚠ Calling Hours: Closed`).


---

## 5. Strict Role-Based Access Control (RBAC) Architecture (Phase 9)

### 5.1 Central Permission System (`backend/accounts/permissions.py`)
- Complete authorization matrix `PERMISSION_MATRIX` mapping 20+ operations across 4 platform roles (`admin`, `manager`, `salesperson`, `surveyor`).
- Central permission evaluator: `can(user, perm_key, obj=None)` combining regional access scoping (`allowed_regions`) and ownership check (`all`, `region`, `own`, `none`, `read_only`, `pending_only`, `remark_only`, `assigned_survey`).
- DRF permission adapters: `DynamicRBACPermission`, `LeadPermission`, `SurveyPermission`, `QuotePermission`.
- **Default Deny**: Any action or route not explicitly mapped is rejected with `HTTP 403 Forbidden`.

### 5.2 Role-Specific Work Areas
- **Admin**: Full system control, master data management, soft delete with mandatory audit reason (`is_deleted=True`), immutable activity corrections (`admin_correction_note`), user & role configuration, privacy governance.
- **Manager**: Regional operations hub, **Manager Attention Queue** (`/manager-attention` with 4 operational tabs: Unassigned leads, Lost approvals pending, Surveys without surveyor, Overdue follow-ups), assignment tools (single, bulk, auto round-robin), read-only team and master views.
- **Salesperson**: Dedicated sales workbench, owns assigned leads only. Cannot assign/reassign, bulk-assign, export, import, or merge. When an outcome leads to `Lost`, routes to `Lost approval pending` (`LOST_APPROVAL_PENDING`) and alerts regional managers.
- **Surveyor**: Field inspection portal (`/my-surveys`), direct calling (`tel:`) and Google Maps navigation. Completely isolated from `/api/leads/` list (`HTTP 403`). Field-level stripping on API responses (no quotes, prices, financial metrics, sales remarks, or marketing sources).

---

## 6. Product Tour and In-App Help Assistant Architecture (Phase 13)

### 6.1 Professional Product Tour System
- **Driver.js v1 Integration**: Lightweight spotlight walkthroughs configured with custom CSS tokens (`.solar-tour-popover`) matching Mantine theme tokens.
- **Server-Side Persistence (`UserTourState`)**:
  - Model: `backend/accounts/models.py:UserTourState` tracks `has_seen_tour`, `tour_version = 1`, `completed_tours` list, `dismissed_at`, and `checklist_state`.
  - Endpoints: `GET /api/me/tour/`, `PATCH /api/me/tour/`, and `POST /api/me/tour/` (reset action).
- **Modular Tour Catalog (`frontend/src/tours/tourDefinitions.ts`)**:
  - Full 3-minute complete system tour.
  - Specialized topic tours: Getting started, Leads & retry ladder, Site surveys, Quotes & proposals, CSV bulk import, Multi-country settings, Notifications, and Admin hub.
  - Stable `data-tour="..."` DOM anchors ensuring resilience across layout changes.
- **Tour Center Drawer (`TourCenterDrawer.tsx`)**:
  - Accessible from the header compass button and user profile menu.
  - Lists tours filtered by user role with duration badges, completion markers, and instant replay capability.
- **Brevo-Style "Get Started" Checklist (`GetStartedChecklist.tsx`)**:
  - Displayed prominently on the Dashboard for new users.
  - Role-tailored tasks with progress percentage bar, auto-checking, and collapsible state.

### 6.2 Help Assistant Chatbot (`helpbot` Module)
- **Zero-Dependency Core**: Operates 100% locally in-process with zero API keys required (`HELPBOT_PROVIDER=local`). Optional Anthropic Claude integration (`HELPBOT_PROVIDER=anthropic`) with automatic fallback to local retrieval.
- **Hybrid NLP Pipeline (`backend/helpbot/nlp.py`)**:
  1. *Prompt Injection Defense*: Detects jailbreaks, prompt override attempts, and system prompt extractors.
  2. *PII Sanitization*: Regex-masks customer phone numbers, emails, passwords, and secret tokens before processing or logging.
  3. *Normalizer*: Handles Indian Hinglish (`kya`, `kaise`, `karna`, `bhejo`) and Australian vernacular (`arvo`, `brekkie`, `rego`, `sparkie`).
  4. *Intent Classifier*: Scikit-learn `TfidfVectorizer` (unigrams + bigrams) paired with a calibrated `LogisticRegression` trained on `helpbot/training/intents.yaml`.
  5. *Rank-BM25 Passage Retriever*: Indexes structured Markdown knowledge articles (`helpbot/knowledge/*.md`) alongside dynamic live database facts (`helpbot/data/dynamic_facts.json`).
  6. *Scope Gate*: Strict software-only perimeter. Politeness-refuses general world questions (weather, jokes, coding, cooking, medical/legal advice) and generates 3 relevant CRM starter suggestions.
- **Live Dynamic Knowledge Indexing (`python manage.py build_helpbot_index`)**:
  - Queries active `PolicySettings`, `Region`, `Outcome`, and `LostReason` records to inject live operational constraints into the search index.
- **Telemetry, Auditing, and Admin Insights**:
  - `HelpbotQueryLog`: Records queries, topics, confidence scores, providers used, and user feedback ratings (`helpful: true/false`).
  - `HelpbotUnanswered`: Captures out-of-scope or low-confidence queries for administrator review and documentation planning.
  - Admin Insights Tab (`HelpbotInsightsTab.tsx`): Displays query volumes, refusal rates, helpful ratings, top queried topics, and a one-click "Rebuild Knowledge Index" trigger.

