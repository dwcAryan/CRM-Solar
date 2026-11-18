---
topic: email_smtp
title: Email and SMTP Setup
keywords: email, smtp, email backend, starttls, ssl, morning digest, overdue reminder, mailgun, sendgrid, gmail
roles: [admin, manager]
regions: [IN, AU]
---
# Email and SMTP Setup

The CRM includes a robust centralized email service supporting SMTP providers (Gmail, Zoho, Brevo, SES, Outlook).

## Email Features
1. **Morning Digest**: Automatically sent every morning at 8:00 AM (in the user's timezone) listing pending follow-ups and newly assigned leads.
2. **Overdue Call Reminders**: Alerts managers and sales reps when high-priority leads have passed their scheduled callback time.
3. **Proposals & Receipts**: Branded HTML emails with quote PDF attachments sent directly to customers.

## Configuration Rules
- Settings are managed in `backend/.env` (and configurable via Admin master settings).
- **Security Check**: The system validates that `EMAIL_USE_TLS` (port 587) and `EMAIL_USE_SSL` (port 465) are never enabled simultaneously.
- **Opt-out Compliance**: Leads with `do_not_contact=True` or an opt-out preference will never be sent marketing or automated emails.
