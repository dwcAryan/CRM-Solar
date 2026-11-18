# Solar CRM - Non-Developer Quick Start Guide

Welcome to **Solar CRM**, a streamlined Customer Relationship Management and sales execution platform designed specifically for residential and commercial solar installers across **India (IN)** and **Australia (AU)**.

---

## What the Project Is

Solar CRM guides sales teams, site surveyors, and regional managers through the complete solar customer journey:
- Managing enquiries and leads across marketing channels (referrals, website, Meta/Google ads).
- Automated follow-up scheduling with mandatory next-action tracking and time-zone compliant calling windows.
- Conducting on-site technical rooftop feasibility inspections with mobile-friendly photo uploads.
- Generating transparent solar proposals with region-specific taxes, currency units, and government subsidies/rebates (India PM Surya Ghar subsidy; Australia CEC STCs and state battery rebates).
- Strict role-based security protecting commercial data while empowering each team member in their dedicated workspace.

---

## Technologies Used & Why

* **PostgreSQL**: High-performance relational database ensuring bulletproof ACID transaction safety, JSON data storage, and audit logs.
* **Django & Django REST Framework (DRF)**: Rock-solid Python backend framework delivering robust security, built-in ORM, and fast RESTful API endpoints.
* **React**: Leading declarative user interface library for crafting responsive, interactive web applications.
* **Vite**: Next-generation frontend build tool providing near-instant dev server startup and hot module reloading.
* **TypeScript**: Type-safe JavaScript ensuring fewer runtime bugs and seamless contract alignment between backend and frontend.
* **Mantine UI**: Comprehensive, accessible component library offering polished forms, date pickers, notifications, and mobile drawers.
* **TanStack Query**: High-performance server-state management handling background data synchronization, caching, and optimistic UI updates.
* **APScheduler**: Lightweight, in-process Python scheduler running automated morning follow-up and evening survey reminder jobs without requiring Redis or Celery.
* **JWT (JSON Web Tokens)**: Secure, stateless token authentication with automated sliding-session refresh rotation.
* **phonenumbers & tzdata**: Industry-standard Google libphonenumber port and IANA time zone database powering international E.164 phone normalization, SMS validation, and calling-hours compliance across India and Australian states.
* **Anthropic Messages API**: State-of-the-art Claude AI integration delivering context-aware sales suggestions, objection handling, and lead win strategies directly inside the CRM.

---

## Folder Map

```text
Solar CRM/
├── run.py                 # Unified cross-platform startup and environment manager
├── start.bat              # One-click Windows starter (double-click to launch)
├── start.sh               # One-click Mac/Linux starter (bash start.sh)
├── HOW_TO_RUN.md          # This user manual and installation guide
├── TECH_STACK.md          # Comprehensive library, dependency, and license manifest
├── pytest.ini             # Pytest test runner configuration
│
├── backend/               # Django REST API Backend
│   ├── accounts/          # User authentication, RBAC permission matrix, user models
│   ├── activities/        # Call/meeting activity logging, immutable audit corrections
│   ├── ai_assist/         # Anthropic Claude & smart rule-based suggestion engines
│   ├── leads/             # Lead pipeline, CSV batch importer, compliance policies
│   ├── masters/           # Region masters, states, lead sources, lost/nurture reasons
│   ├── messaging/         # WhatsApp & SMS provider gateways, message templates
│   ├── notifications/     # Notification system & APScheduler background jobs
│   ├── quotes/            # Solar quotation builder, STCs, tax calculators, PDF export
│   ├── surveys/           # Site inspection bookings, surveyor portal, photo uploads
│   ├── requirements.txt   # Backend Python package manifest
│   ├── manage.py          # Django administrative tool
│   └── .env.example       # Example backend configuration variables
│
├── frontend/              # React + Mantine Frontend Single-Page App
│   ├── src/               # Application source code (components, pages, context, api)
│   ├── package.json       # Frontend npm package dependencies
│   ├── vite.config.ts     # Vite build and development configuration
│   └── playwright.config.ts # Playwright end-to-end browser test configuration
│
├── scripts/               # Helper utilities
│   ├── stop.bat / .sh     # Cleanly terminates all running backend/frontend processes
│   ├── backup-db.bat / .sh# Creates timestamped PostgreSQL backups in backups/
│   └── restore-db.bat / .sh# Interactive, safe database restore utility
│
├── backups/               # Timestamped database dumps (*.dump, git-ignored)
└── docs/                  # System architecture, RBAC specs, and generated demo logins
    ├── ARCHITECTURE.md    # Technical design, database models, and workflow specs
    ├── ROLES_AND_PERMISSIONS.md # Comprehensive Role-Based Access Control matrix
    └── DEMO_ACCOUNTS.md   # Dynamic demo logins and random passwords (git-ignored)
```

---

## One-Time Installation Checklist

Before starting the CRM for the first time, ensure these free software prerequisites are installed on your computer:

| Prerequisite | Minimum Version | Download Link & Notes |
|:---|:---|:---|
| **Python** | 3.12 or higher | [Download Python](https://www.python.org/downloads/) — *Important:* Check the box **"Add Python to PATH"** during installation. |
| **Node.js** | 18+ LTS | [Download Node.js](https://nodejs.org/) — Includes `npm` package manager automatically. |
| **PostgreSQL** | 16 or higher | [Download PostgreSQL](https://www.postgresql.org/download/) — Ensure the PostgreSQL service is running on default port `5432`. |
| **Git** | 2.30+ | [Download Git](https://git-scm.com/downloads) |

### Database Quick Setup
1. Open pgAdmin or your PostgreSQL command line (`psql`).
2. Create the database and user configured in `backend/.env` (or let `run.py` guide you):
   ```sql
   CREATE DATABASE solar_crm;
   CREATE USER solar_user WITH PASSWORD 'SolarUser_2026_SecurePass!88';
   GRANT ALL PRIVILEGES ON DATABASE solar_crm TO solar_user;
   ALTER DATABASE solar_crm OWNER TO solar_user;
   ```

---

## How to Start

### Option A: Windows (One Double-Click)
Simply double-click the **`start.bat`** file in the project folder.

### Option B: macOS / Linux (One Terminal Command)
Open your terminal in the project folder and run:
```bash
./start.sh
```

### Option C: Universal Python Command
From any command prompt or terminal in the project directory:
```bash
python run.py
```

### What `run.py` Handles Automatically:
1. Verifies Python 3.12+, Node.js, npm, and PostgreSQL socket connectivity.
2. Creates `backend/.env` from `.env.example` if missing.
3. Creates `backend/venv` and installs Python dependencies directly using the venv's python binary (no virtual environment activation required).
4. Runs `npm install` in `frontend` only when package manifests change (smart caching).
5. Applies database migrations and seeds idempotent masters (regions, Australian states, Indian states, solar equipment types).
6. Checks if demo data exists. If empty, prompts to seed sample leads and generates fresh credentials.
7. Concurrently starts the Django REST API (`http://localhost:8000`), Vite Dev Server (`http://localhost:5173`), and APScheduler in child processes with live color-coded logs.
8. Opens your default web browser to the CRM login page.

### Useful Command Flags
You can run `python run.py [FLAG]`:
- `--no-browser`: Do not auto-launch the web browser.
- `--skip-install`: Skip checking and updating pip/npm dependencies for ultra-fast startup.
- `--backend-only`: Run only the Django API server.
- `--reset-demo`: Clear existing sample leads and regenerate fresh demo accounts with new secure passwords.

---

## Application URLs

Once started, access the application at:

| Component | URL | Description |
|:---|:---|:---|
| **Frontend Web App** | [http://localhost:5173](http://localhost:5173) | Main single-page application for all users (Sales, Managers, Surveyors, Admins). |
| **Backend REST API** | [http://localhost:8000/api/](http://localhost:8000/api/) | REST API root endpoints. |
| **API Documentation** | [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/) | Interactive OpenAPI / Swagger documentation and sandbox. |
| **Django Admin** | [http://localhost:8000/admin/](http://localhost:8000/admin/) | System administrative back-office portal. |

> [!NOTE]
> **Desktop PWA & Push Notification Security Requirements:**
> Web browsers (Chrome, Edge, Safari, Brave) require a secure origin to enable Service Workers, the **"Download for desktop"** PWA installation button, and Web Push notifications.
> - **Local Development:** `http://localhost:5173` or `http://127.0.0.1:5173` is considered secure by default.
> - **Production Deployment:** Must be served over **HTTPS** with a valid TLS/SSL certificate. Accessing via plain HTTP over non-localhost IP addresses will prevent app installation and push subscription prompts.

---

## Where to Find Demo Logins

For security, **passwords are never hardcoded or stored in public documents**.

When the system initializes sample data, it generates strong randomized credentials for each role and records them in:
```text
docs/DEMO_ACCOUNTS.md
```
*(This file is created on your machine and is ignored by git).*

Open `docs/DEMO_ACCOUNTS.md` to find usernames and active passwords for:
- **`demo_admin`**: System Administrator (Full access, user management, audit governance).
- **`demo_manager`**: Regional Sales Manager (Manager Attention Queue, lead distribution, lost deal approvals).
- **`demo_sales_in`**: India Salesperson (India pipeline, call logs, WhatsApp reminders, quotes).
- **`demo_sales_au`**: Australia Salesperson (Australian pipeline, DNCR consent checks, STC proposals).
- **`demo_surveyor_in`**: India Technical Surveyor (Mobile site feasibility portal, photo uploads).
- **`demo_surveyor_au`**: Australia Technical Surveyor (Switchboard & solar inspection portal).

---

## How to Stop

To stop all Solar CRM services:
1. In the terminal window running `run.py`, press **`Ctrl + C`**. All processes shut down cleanly.
2. Alternatively, run the stop helper script:
   - **Windows:** Double-click `scripts/stop.bat`
   - **macOS / Linux:** Run `./scripts/stop.sh`

---

## How to Back Up and Restore Database

### Back Up Database
To create a safe, compressed timestamped backup of all leads, users, and activities:
- **Windows:** Double-click `scripts/backup-db.bat`
- **macOS / Linux:** Run `./scripts/backup-db.sh`
- Backups are saved to `backups/solar_crm_backup_YYYYMMDD_HHMMSS.dump`.

### Restore Database
To restore data from an existing backup:
- **Windows:** Double-click `scripts/restore-db.bat`
- **macOS / Linux:** Run `./scripts/restore-db.sh`
- The script displays all available backups, lets you choose by number, and asks for explicit confirmation before restoring.

---

## How to Turn on the AI Suggestion Key

Solar CRM includes an AI sales coach that analyzes customer interactions and recommends next steps.

1. Open `backend/.env` in any text editor.
2. Locate the AI configuration section:
   ```env
   AI_PROVIDER=anthropic
   ANTHROPIC_API_KEY=your_actual_anthropic_api_key_here
   AI_MODEL=claude-sonnet-5-5
   AI_TIMEOUT_SECONDS=15
   AI_MAX_CALLS_PER_USER_PER_DAY=50
   ```
3. Save the file and restart Solar CRM (`python run.py`).
4. *Note:* If no API key is provided (`AI_PROVIDER=rules`), Solar CRM automatically falls back to its built-in rule engine, providing smart suggestions without any external API or extra cost!

---

## How to Update the Project

When updates or new features are pulled from the repository:
```bash
git pull origin release/v1.0
python run.py
```
`run.py` will automatically detect updated packages, apply new database migrations, and verify seed data.

---

## Regions and Time Zones

Solar CRM is built ground-up to support multi-country solar operations:

### Environment Settings (`backend/.env`)
- **`ENABLED_COUNTRIES`**: Comma-separated country codes (default: `IN,AU`). Setting `ENABLED_COUNTRIES=IN` restricts the system strictly to India; `ENABLED_COUNTRIES=AU` restricts to Australia.
- **`SMS_PROVIDER`**: Controls the SMS delivery engine (`console` for development logging or `twilio` for production).
- **`WHATSAPP_PROVIDER`**: Controls WhatsApp messaging (`console` or provider API).

### Time Zone & Calling Hours Rules
- **India (IN)**: Standardized across the country on `Asia/Kolkata` (UTC+5:30).
- **Australia (AU)**: Multi-timezone support across states:
  - New South Wales (NSW), Victoria (VIC), Tasmania (TAS), ACT: `Australia/Sydney`, `Australia/Melbourne`, `Australia/Hobart` (AEST/AEDT).
  - Queensland (QLD): `Australia/Brisbane` (AEST, no daylight saving).
  - South Australia (SA): `Australia/Adelaide` (ACST/ACDT).
  - Western Australia (WA): `Australia/Perth` (AWST).
  - Northern Territory (NT): `Australia/Darwin` (ACST).
- **Calling Compliance**: The system calculates the lead's local time based on their state/postcode and restricts automated or manual marketing calls outside 9:00 AM – 8:00 PM local customer time, respecting national telemarketing standards and Do Not Call Register (DNCR) rules.

---

## Setting up Email (SMTP)

Solar CRM delivers automated 9:00 AM follow-up digests, 6:00 PM site inspection reminders, new lead assignment alerts, and secure 1-hour password reset links.

### 1. How to Generate an App Password (Gmail / Google Workspace)
If you use Gmail or Google Workspace:
1. Go to your **Google Account** settings (`https://myaccount.google.com/`).
2. Navigate to **Security** and confirm **2-Step Verification** is turned **ON**.
3. Under *How you sign in to Google*, click on **App passwords** (or search "App passwords").
4. Enter an app name (e.g. `Solar CRM`), click **Create**, and copy the 16-character passkey (e.g., `dgqbgjjlmxiilrfu`).

### 2. Where to Paste the Settings
Open `backend/.env` in your code editor and populate the email parameters:
```env
EMAIL_BACKEND=smtp
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_16_char_app_password
DEFAULT_FROM_EMAIL="Solar CRM <your_email@gmail.com>"
EMAIL_TIMEOUT=15
```
*(Note: If `EMAIL_BACKEND=console` or left unset in development, emails are safely logged to your server console without transmission).*

### 3. How to Run `check_email`
To verify your SMTP handshake, TLS encryption, and login credentials without starting the frontend:
```bash
# Verify credentials and server connectivity (password is masked):
python backend/manage.py check_email

# Send a real live test email to any recipient:
python backend/manage.py check_email --to name@example.com
```

### 4. SMTP Troubleshooting Table

| Problem | Cause | Solution |
|:---|:---|:---|
| **535 Authentication Failed** | Incorrect login credentials or standard Google password used instead of an App Password. | Ensure 2-Step Verification is active on your Google account. Generate a fresh 16-character App Password and paste it into `EMAIL_HOST_PASSWORD` without spaces. |
| **Connection Refused** | Outgoing SMTP host or port is incorrect, or local mail server is offline. | Double-check `EMAIL_HOST` (e.g. `smtp.gmail.com`) and `EMAIL_PORT` (`587` for STARTTLS, `465` for SSL). Never enable both TLS and SSL simultaneously. |
| **Connection Timeout** | Port 587 or 465 is blocked by your local network, router firewall, or ISP. | Switch networks (e.g. test via mobile hotspot) or adjust firewall egress rules to allow outbound TCP connections on port 587. |
| **Emails landing in Spam / Junk** | Sending from an unauthenticated IP address, or recipient mail filter has strict DMARC rules. | Add the sender address to your contacts. For business domains, configure SPF and DKIM DNS records as outlined below. |
| **SPF & DKIM for Custom Domain** | Recipient mail providers (Gmail/Outlook) reject or quarantine custom domain emails lacking DNS authentication. | In your DNS provider (Cloudflare, GoDaddy, Namecheap):<br>1. **SPF:** Add a TXT record for `@` with value `v=spf1 include:_spf.google.com ~all` (or your provider's SPF).<br>2. **DKIM:** Generate a 2048-bit DKIM key in your Google Workspace/Zoho/Brevo admin panel and add the TXT record to your DNS.<br>3. **DMARC:** Add a TXT record `_dmarc.yourdomain.com` with `v=DMARC1; p=none; sp=none;`. |

---

## Product Tour & In-App Help Assistant (Phase 13)

### 1. Interactive Product Tour
* **Automatic Onboarding**: New users receive a guided walkthrough spotlighting navigation, leads, surveys, and quotes upon first login.
* **Tour Center**: Click the compass icon in the header or select **Product Tour Center** from the user profile dropdown to launch specialized modular walkthroughs (Getting Started, Leads & Retry Ladder, Surveys, Quotes, CSV Import, Regions, Notifications).
* **Resetting Tours**: Admins or users can reset tour completion states anytime from the Tour Center drawer.

### 2. Help Assistant Chatbot (`helpbot`)
* **Quick Access**: Click the floating assistant button in the bottom right corner or press `?` on your keyboard from any screen to open the Help Assistant.
* **Scope-Gated Knowledge**: The assistant strictly answers questions about using this CRM application (call outcomes, retry rules, site surveys, pricing proposals, role permissions, and policies) and politely declines unrelated inquiries.
* **Show Me How**: Whenever an answer relates to a feature with a guided tour, click the **Show me how** button directly inside the chat response to jump straight into the interactive walkthrough!
* **Rebuilding Knowledge Index**:
  ```bash
  python backend/manage.py build_helpbot_index --force
  ```
  This command parses markdown articles in `backend/helpbot/knowledge/`, extracts live dynamic policies from PostgreSQL, trains the in-process NLP intent classifier, and updates the BM25 search index.

---

## Troubleshooting Guide

| Problem | Cause | Solution |
|:---|:---|:---|
| **Port 8000 or 5173 in use** | A previous instance of Django or Vite is still running in the background. | Run `scripts/stop.bat` (Windows) or `./scripts/stop.sh` (Mac/Linux) to kill any dangling processes, then restart. |
| **Database connection refused (`localhost:5432`)** | PostgreSQL service is stopped or port is blocked. | **Windows:** Press `Win+R`, type `services.msc`, locate `postgresql-x64-*`, right-click and select **Start**.<br>**Mac:** `brew services start postgresql`<br>**Linux:** `sudo systemctl start postgresql`. |
| **Forgot password for demo account** | Passwords were regenerated or forgotten. | Open `docs/DEMO_ACCOUNTS.md`. If you need fresh credentials, run `python run.py --reset-demo`. |
| **Python venv errors or missing packages** | Virtual environment was interrupted or corrupted during creation. | Delete the `backend/venv` folder and run `python run.py`. The runner will reconstruct the virtual environment automatically. |
| **Frontend npm errors or build failures** | Stale node modules or interrupted install. | Delete the `frontend/node_modules` folder and run `python run.py`. |
| **CSV Lead Import fails on upload** | File headers don't match or invalid phone numbers. | Download the sample CSV template directly from the Import page. Ensure Indian phone numbers have 10 digits and Australian numbers have valid mobile prefixes (e.g. `04XX XXX XXX`). |
