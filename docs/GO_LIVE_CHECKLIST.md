# Solar CRM — Production Go-Live & Deployment Checklist

**Release Version:** 1.0.0  
**Effective Date:** November 2026  
**Target Environments:** Production Hosting (India & Australia)

---

## 1. Executive Pre-Flight Summary

This checklist outlines the mandatory operational, architectural, and statutory compliance steps required before deploying Solar CRM into a live commercial environment. Every item must be verified and signed off by the platform administrator and designated compliance lead.

---

## 2. Infrastructure, Security & Network Configuration

- [ ] **HTTPS & TLS Termination:**
  - Enforce TLS 1.3 / 1.2 across all endpoints via reverse proxy (Nginx, Traefik, or Cloudflare).
  - Set `SECURE_SSL_REDIRECT=True` in production `.env`.
  - Verify HSTS preload headers (`SECURE_HSTS_SECONDS=31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS=True`).
- [ ] **Cryptographic Secrets & Environment Isolation:**
  - Generate a random 64+ character `SECRET_KEY` (e.g. `python -c "import secrets; print(secrets.token_urlsafe(64))"`).
  - Explicitly restrict `ALLOWED_HOSTS` to production domains (no wildcards `*`).
  - Set `CORS_ALLOWED_ORIGINS` strictly to authorized production web apps.
  - Set `APP_BASE_URL` to the public canonical HTTPS URL (used for password reset tokens and email links).
  - Confirm `DEBUG=False` and `APP_ENV=production`.
- [ ] **Firewall & Ingress Rules:**
  - Expose ports 80/443 only. Restrict PostgreSQL database port 5432 strictly to internal application server IP addresses.
  - Ensure rate-limiting is active on `/api/token/`, `/api/auth/password-reset/`, and `/api/helpbot/ask/`.

---

## 3. Data Cleansing & User Provisioning

- [ ] **Purge All Demo & Training Accounts:**
  - Execute `python backend/manage.py remove_demo_data --force` to atomically delete all demo leads, mock activities, and demo accounts (`is_demo=True`).
  - Run `python backend/manage.py check --deploy` to confirm zero demo traps exist in production mode.
- [ ] **Provision Initial Real Administrator:**
  - Run `python backend/manage.py create_admin` interactively to create the primary superuser with verified corporate credentials.
- [ ] **Create Production Staff Accounts:**
  - Create real staff users with assigned roles (`manager`, `salesperson`, `surveyor`) and regional access (`IN`, `AU`).
  - Enable `must_change_password=True` on provisioned accounts to mandate immediate credential rotation on first login.

---

## 4. Email, Messaging & Notifications Setup

- [ ] **SMTP Outbox Verification:**
  - Configure production SMTP credentials in backend `.env` (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`).
  - Test end-to-end deliverability by executing:
    ```bash
    python backend/manage.py check_email --to ops-admin@company.com
    ```
- [ ] **Web Push (VAPID) Key Generation:**
  - Generate production VAPID application keys (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CLAIMS_EMAIL`).
  - Verify web push permissions prompt and in-browser notification arrival.
- [ ] **Customer Communication Provider Approvals:**
  - **India (DLT Registration):** Register Principal Entity and all customer-facing SMS/WhatsApp templates with Telecom Service Provider (DLT portal). Unregistered commercial headers will be rejected by Indian carriers.
  - **Australia (ACMA Sender ID):** Verify registered Alpha-Tag or dedicated virtual mobile number (VMN) with Australian SMS gateway.

---

## 5. Localization & Native Speaker Review

- [ ] **Native Speaker Review of Customer-Facing Templates:**
  - Verify all automated WhatsApp, SMS, and email templates in English and Hindi (and any further active regional dialects).
  - Ensure all dynamic parameters (e.g. `{customer_name}`, `{survey_date}`, `{quote_amount}`) render accurately without syntax truncation.
- [ ] **Opt-Out & Statutory Privacy Notices:**
  - Confirm the exact opt-out footer text on outbound customer messages:
    - *India:* "Reply STOP to opt out of solar updates."
    - *Australia:* "Reply STOP to opt out. ACMA compliant."
- [ ] **Interface Catalog Verification:**
  - Confirm that all master statuses, reasons, and interface strings are reviewed (`status='approved'`) in the Admin Translations portal.

---

## 6. Regional Compliance, Timezones & Holidays

- [ ] **Calling Hours Enforcement:**
  - Verify regional policy settings:
    - *India (`Asia/Kolkata`):* Restrict telemarketing outreach to 09:00–20:00 IST.
    - *Australia (`Australia/Sydney`, `Australia/Perth`):* Restrict calls to 09:00–20:00 weekdays, 09:00–17:00 Saturdays; prohibit Sundays and public holidays.
- [ ] **Gazetted Public Holidays:**
  - Review and load the annual public holidays for each operating state via Admin -> **Public Holidays** master.
- [ ] **Data Sovereignty & Cross-Border Compliance:**
  - In accordance with India's DPDP Act 2023 and Australian Privacy Principles (APP 8), confirm that database backups and primary instances comply with customer data sovereignty requirements.
- [ ] **Statutory Compliance Sign-Off:**
  - Conduct formal legal review with qualified counsel in each jurisdiction to approve call scripts, consent capture mechanisms, and retention schedules.

---

## 7. Backups, Monitoring & Operational Readiness

- [ ] **Automated Database Backups:**
  - Configure a system cron or Windows Task Scheduler job running daily at midnight:
    ```bash
    python scripts/backup_db.py --retention 30
    ```
  - Test database restore capability using `scripts/restore_db.py` in a staging sandbox.
- [ ] **System Health Probing:**
  - Configure external monitoring (e.g. Datadog, UptimeRobot, CloudWatch) to probe `GET /api/health/` every 60 seconds (expects `HTTP 200` with `"status": "ok"`).
- [ ] **Log Retention & Scrubbing:**
  - Confirm log rotation is active with `SensitiveDataFilter` stripping passwords, bearer tokens, and credit card numbers from production log streams.
- [ ] **Support & Incident Escalation Contacts:**
  - **Platform Administrator:** `admin@company.com`
  - **Internal IT Helpdesk:** `support@solar-crm.internal`
  - **Data Protection Officer (DPO):** `privacy@company.com`
