# Solar CRM (India & Australia Multi-Country Edition)

A high-performance, compliant, purpose-built CRM engineered for residential and commercial solar installation businesses operating across **India (IN)** and **Australia (AU)**. Focuses on lead acquisition, call outcomes, site feasibility surveys, and quotation negotiations strictly up to the "Won" milestone.

---

## Core Business Rule

> **Every call, visit, or message must end with an outcome.**
> Each outcome irrevocably sets three fields:
> 1. The **lead status**
> 2. The **next action**
> 3. The **next follow-up date**
>
> A lead without a next follow-up date is prohibited by system validation (except terminal statuses: `Won`, `Lost`, `Do not contact`, `Merged`, `Invalid contact`).

---

## Multi-Country Capabilities (India & Australia)

1. **Configurable Region Architecture**:
   - Master records for India (`IN`) and Australia (`AU`) with zero hardcoded laws, tax rates, or rebate values.
   - Region-specific currencies, symbols (`₹` vs `A$`), phone country codes (`+91` vs `+61`), and dynamic tax rates (GST 5% vs 10%).
   - Dynamic terminology adaptation: "DISCOM" vs "Electricity Retailer", "Subsidy (PM Surya Ghar)" vs "Government Incentive (STCs and Rebates)".
   - Strict currency isolation: Revenue and quotes are segregated per currency code; currencies are never cross-added.

2. **Calling Hours & Timezone Engine**:
   - Evaluates outbound calls and follow-ups in the customer's local timezone (e.g., `Australia/Sydney`, `Australia/Perth`, `Asia/Kolkata`).
   - Complies with Australian calling hours (Mon–Fri 09:00–20:00, Sat 09:00–17:00; Sundays and public holidays blocked) and Indian calling hours (09:00–20:00).
   - Warnings or hard blocks when calling outside permitted hours; requires a typed override reason logged to an immutable audit trail.

3. **Consent & Channel Opt-Outs**:
   - Granular channel opt-outs: `opt_out_calls`, `opt_out_sms`, `opt_out_whatsapp`, `opt_out_email`.
   - Do Not Call Register (DNCR) status tracking (`verified_clean`, `listed`, `unverified`) with warning flags.
   - Dynamic channel prioritization: WhatsApp-first for India; SMS-first for Australia with mandatory opt-out lines ("Reply STOP to opt out").

4. **Privacy & Data Governance (DPDP Act 2023 & Privacy Act 1988)**:
   - **DSAR Dossier Export**: Generate full Data Subject Access Request dossiers in structured JSON or official PDF.
   - **Irreversible Anonymization**: Permanent cryptographic zeroing of PII with tamper-evident audit recording.
   - **Data Rectification**: Update contact info with before/after audit tracking.
   - **Tamper-Evident AuditLog**: Immutable append-only model preventing updates or deletions.

---

## Technology Stack

- **Backend**: Python 3.12+, Django 5, Django REST Framework, SimpleJWT, drf-spectacular, ReportLab (PDF dossiers), APScheduler, phonenumbers, pytz, psycopg (v3)
- **Frontend**: React 18+, Vite, TypeScript, Mantine UI, TanStack Query, React Router, Axios, Tabler Icons
- **Database**: PostgreSQL 16+ (Local installation)

---

## Project Structure

```
solar-crm/
  backend/          # Django project ("config") & modular apps
    accounts/       # Custom user model with roles, allowed_regions, and default_region
    masters/        # Region masters, States, RoofTypes, Outcome matrix, PolicySettings
    leads/          # Multi-country leads, phone normalization, privacy service, and audit logs
    activities/     # Follow-up logs, calling hours checks, and outcome transitions
    surveys/        # Site surveys, schedule tracking, and site photos
    quotes/         # Versioned proposals with regional tax, incentive, and battery snapshots
    messaging/      # WhatsApp/SMS multi-channel message logs & templates
    notifications/  # APScheduler daily follow-up and survey reminders
    ai_assist/      # Regional AI recommendations & rules-based fallback copilot
  frontend/         # Vite React TypeScript application with Mantine UI
  docs/             # Process definitions, User Manual, and Compliance Notes
```

---

## Documentation

- **Compliance & Legal Notes**: [`docs/COMPLIANCE_NOTES.md`](docs/COMPLIANCE_NOTES.md) (DPDP Act 2023, TRAI, Privacy Act 1988/APPs, Spam Act 2003, DNCR Act 2006).
- **User & Operations Manual**: [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md)
- **Process Specification**: `docs/Solar CRM – All Process Paths and Outcomes (v0.1).pdf`

---

## Getting Started

### 1. Database Setup
Create database `sky_electrical_solar` in your local PostgreSQL:
```sql
CREATE DATABASE sky_electrical_solar;
```

### 2. Backend Setup
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_masters
python manage.py seed_demo
python manage.py runserver
```
- Swagger API Docs: `http://localhost:8000/api/docs/`
- Django Admin: `http://localhost:8000/admin/`

### 3. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```
Runs at `http://localhost:5173`.

---

## Demo Credentials

All demo accounts use the standard password: `Admin@Demo2026!` (Admin), `Manager@Demo2026!` (Manager), `Sales@Demo2026!` (Sales), or `Surveyor@Demo2026!` (Surveyor):

| Role | Username | Password | Regions |
| :--- | :--- | :--- | :--- |
| **Admin** | `demo_admin` | `Admin@Demo2026!` | India & Australia |
| **Manager** | `demo_manager` | `Manager@Demo2026!` | India & Australia |
| **Salesperson (India)** | `demo_sales_in` | `Sales@Demo2026!` | India |
| **Salesperson (Australia)**| `demo_sales_au` | `Sales@Demo2026!` | Australia |
| **Surveyor (India)** | `demo_surveyor_in` | `Surveyor@Demo2026!` | India |
| **Surveyor (Australia)** | `demo_surveyor_au` | `Surveyor@Demo2026!` | Australia |

---

## Testing

Run the automated test suite (73 passing tests covering business logic, privacy, calling hours, CSV import, and multi-country features):
```powershell
backend/venv/Scripts/python.exe -m pytest backend/tests/
```
Run frontend TypeScript and production build:
```powershell
npm --prefix frontend run build
```
