# Departments (Operational Guide)

## Overview

Departments partition data and permissions in multi-department installations.

Typical goals:

- one installation for multiple departments
- department-scoped users only work in assigned departments
- org-wide users can work across all departments

## Core API Endpoints

- `GET /api/v1/departments/`
- `POST /api/v1/departments/`
- `PATCH /api/v1/departments/{id}/`
- `DELETE /api/v1/departments/{id}/`
- `GET /api/v1/admin/department-roles/`
- `POST /api/v1/admin/department-roles/`

## Practical Behavior

- Department-aware ViewSets filter list data by the active/allowed department context.
- Org-wide access is granted by staff/superuser or `departments.can_access_all_departments`.
- Department role assignments connect users, departments, and auth groups.

## Where Departments Interact With Other Features

- Member and group visibility uses department scoping rules.
- LDAP mappings can assign department roles from LDAP groups.
- OIDC mappings can assign department roles from token group claims.
- External sync can run in department scope and can map Spond groups to departments.

## Related References

- Deep technical architecture: `docs/architecture/departments-and-permissions.md`
- Settings, LDAP, SSO: `docs/domains/settings-ldap-sso.md`
- External sync: `docs/domains/external-sync-spond.md`
