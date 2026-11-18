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
