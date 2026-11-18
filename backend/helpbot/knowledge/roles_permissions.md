---
topic: roles_permissions
title: User Roles and Strict Access Control (RBAC)
keywords: roles, permissions, rbac, admin, manager, salesperson, surveyor, access control, restrictions
roles: [admin, manager, salesperson, surveyor]
regions: [IN, AU]
---
# User Roles and Strict Access Control

The Solar CRM enforces strict Role-Based Access Control (RBAC). Buttons, menus, and API routes are strictly restricted by user role.

## The Four Roles
1. **Admin**:
   - Full system access.
   - User account creation, role assignments, region assignments.
   - Master settings, Policy Settings, Regions, Email/SMTP configuration, Helpbot management.
2. **Manager**:
   - Team supervision, bulk lead assignment, re-assignment.
   - CSV lead imports, export reports.
   - Lost lead approvals and review.
   - Lead analytics and team performance metrics.
3. **Salesperson**:
   - View and manage assigned leads in permitted regions.
   - Log customer calls, schedule follow-ups.
   - Request site surveys and generate quotes/proposals.
   - *Restrictions*: Cannot reassign leads, cannot view unassigned team pools unless permitted, cannot import bulk CSV or change system policies.
4. **Surveyor**:
   - Access to dedicated Surveyor Workspace.
   - View assigned site surveys with customer address and contact.
   - Fill survey inspection forms, take measurements, and upload photos.
   - *Restrictions*: Cannot view financial quotes, bulk lead lists, or admin settings.
