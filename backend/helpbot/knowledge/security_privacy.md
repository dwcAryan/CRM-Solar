---
topic: security_privacy
title: Security, Privacy, and Audit Compliance
keywords: security, privacy, pii, audit logs, passwords, permissions, encryption, role boundary
roles: [admin, manager, salesperson, surveyor]
regions: [IN, AU]
---
# Security, Privacy, and Data Protection

The Solar CRM adheres to strict data protection standards, role segregation, and comprehensive audit tracking.

## Core Protections
1. **PII Masking & Privacy**: Customer phone numbers and emails are only accessible to team members with assigned pipeline responsibilities. Direct exports are restricted to Managers and Admins.
2. **Audit Logging**: Sensitive operations (reassignments, bulk status changes, export requests, policy modifications) generate immutable audit logs.
3. **No Secrets in Logs or Chatbot**: Helpbot and logs strictly sanitize passwords, SMTP credentials, API tokens, and customer identity markers.
4. **Session & Role Boundaries**: Every API endpoint verifies permissions independently. Direct URL tampering or API forgery attempts are blocked with HTTP 403 Forbidden.
