# Solar CRM — Roles and Permissions (RBAC) Architecture

## 1. Overview & Security Model
Solar CRM enforces a strict **Centralized Role-Based Access Control (RBAC)** architecture paired with **Multi-Region Data Scoping**.

Every request is evaluated under a **Strict Default Deny** policy:
- If a route, action, or method is not explicitly mapped in `PERMISSION_MATRIX` (`backend/accounts/permissions.py`), it is automatically refused with `HTTP 403 Forbidden`.
- Client-side visibility is synchronized with server-side authorization: users never see buttons, tabs, forms, or nav items they are unauthorized to execute.

---

## 2. Platform Roles & Scopes

| Role | Operational Scope | Description |
| :--- | :--- | :--- |
| **Admin** | System-wide (`all`) | Complete control over platform users, master data editing, immutable activity corrections, privacy dossiers/erasure, audit logs, and soft deletion. |
| **Manager** | Regional (`region`) | Regional oversight across allowed regions. Manages staff assignments (single, bulk, auto round-robin), approves/rejects Lost requests, staffs surveys, and views team performance. Read-only access to masters. |
| **Salesperson** | Own Records (`own`) | Dedicated sales workbench. Sees only leads assigned to them. Cannot assign/reassign, bulk-assign, export, import, or merge. Cannot finalize Lost directly (submits for manager approval). |
| **Surveyor** | Assigned Inspections (`own` / `assigned_survey`) | Field inspection mobile portal. Completely isolated from leads list (`HTTP 403` on `/api/leads/`). Sees only assigned inspections via `/my-surveys`. Sensitive fields (prices, quotes, sales remarks, marketing sources) are strictly stripped. |

---

## 3. Permission Keys & Matrix Summary

| Area | Permission Key | Admin | Manager | Salesperson | Surveyor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Leads** | `lead.view` | all | region | own | none |
| | `lead.create` | all | region | own | none |
| | `lead.edit` | all | region | own | none |
| | `lead.delete` | all | none | none | none |
| | `lead.assign` | all | region | none | none |
| | `lead.unassigned_queue` | all | region | none | none |
| | `lead.lost_approval` | all | region | none | none |
| | `lead.manual_status_change`| all | region | none | none |
| | `lead.merge` | all | region | none | none |
| | `lead.export` | all | region | none | none |
| | `lead.import` | all | region | none | none |
| | `lead.bulk_action` | all | region | remark_only | none |
| **Surveys** | `survey.view` | all | region | own | own |
| | `survey.book` | all | region | own | none |
| | `survey.assign` | all | region | none | none |
| | `survey.reschedule` | all | region | own | own |
| | `survey.complete` | all | region | none | own |
| **Quotes** | `quote.view` | all | region | own | none |
| | `quote.create` | all | region | own | none |
| | `quote.send` | all | region | own | none |
| | `quote.revise` | all | region | own | none |
| | `quote.accept` | all | region | own | none |
| | `quote.reject` | all | region | own | none |
| **Activities**| `activity.view` | all | region | own | none |
| | `activity.log` | all | region | own | assigned_survey |
| | `activity.correct` | all | none | none | none |
| **System** | `user.manage` | all | none | none | none |
| | `user.view_team` | all | region | none | none |
| | `masters.manage` | all | read_only | none | none |
| | `privacy.manage` | all | none | none | none |
| | `audit.view` | all | none | none | none |

---

## 4. Key Workflows & Boundary Guarantees

### A. Salesperson "Lost Approval Pending" Workflow
- When a salesperson logs an outcome that defaults to `Lost`, the lead does NOT transition to terminal Lost immediately.
- The lead status transitions to `Lost approval pending` (`LOST_APPROVAL_PENDING`).
- The submission records `lost_pending_reason` and `lost_pending_notes`, and immediately notifies all regional managers.
- A regional manager inspects the submission in the **Manager Attention Queue** (`/manager-attention`):
  - **Approve**: Lead transitions to terminal `Lost`.
  - **Reject**: Manager provides rejection reason and required next follow-up date; lead reverts to previous active pipeline status and salesperson is notified.

### B. Surveyor Data Isolation & Field Stripping
- Surveyors are refused with `HTTP 403 Forbidden` on `/api/leads/`, `/api/quotes/`, `/api/activities/`, and `/api/roles-matrix/`.
- Surveyors access their assigned inspections via `/api/surveys/my-surveys/`.
- `LeadSerializer.to_representation` and `SurveySerializer.to_representation` automatically strip sensitive financial and sales fields (quotes, system prices, monthly power bills, sales remarks, consent records, and status history).

### C. Activity Immutability & Admin Corrections
- Activities are append-only. `PUT`, `PATCH`, and `DELETE` requests on `/api/activities/{id}/` are refused with `HTTP 403`.
- If a note or record contains an error, an Administrator can append an official `admin_correction_note` via `POST /api/activities/{id}/add-correction/`, preserving the complete original audit trail.

### D. Soft Deletion with Mandatory Audit Reason
- Lead deletion (`DELETE /api/leads/{id}/`) is restricted exclusively to Administrators.
- A deletion reason is mandatory (`HTTP 400` if omitted).
- Deleted leads are soft-deleted (`is_deleted=True`, `deleted_by`, `deleted_at`, `deleted_reason`), recorded in `AuditLog`, and excluded from all regular queries and dashboards.

### E. Privilege Escalation Prevention
- Profile updates via `PATCH /api/me/` strictly reject modifications to privileged fields (`role`, `is_staff`, `is_superuser`, `allowed_regions`, `default_region`, `is_active`) with `HTTP 403 Forbidden`.
