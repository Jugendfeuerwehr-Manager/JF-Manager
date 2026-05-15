# Members, Lists, Group Editor, And Excel Exports

## Overview

This guide documents the member-related features that were recently expanded:

- Member lists (attendance/check lists)
- Group editor (member groups and permission groups)
- Excel export with selectable columns

## UI Entry Points

- Members: `/members`
- Lists: `/lists`
- List detail: `/lists/:id`
- Group management (member groups): `/groups`
- Admin users and permission groups: `/users`

## Member Lists

Member lists are managed via `MemberListViewSet` and support both CRUD and workflow actions.

Core endpoints:

- `GET /api/v1/member-lists/`
- `GET /api/v1/member-lists/{id}/`
- `POST /api/v1/member-lists/`
- `PATCH /api/v1/member-lists/{id}/`
- `DELETE /api/v1/member-lists/{id}/`

List workflow actions:

- `POST /api/v1/member-lists/{id}/add_member/`
- `POST /api/v1/member-lists/{id}/remove_member/`
- `POST /api/v1/member-lists/{id}/bulk_add/`
- `POST /api/v1/member-lists/{id}/toggle_check/`
- `POST /api/v1/member-lists/{id}/set_check/`
- `POST /api/v1/member-lists/{id}/check_all/`
- `POST /api/v1/member-lists/{id}/uncheck_all/`
- `PATCH /api/v1/member-lists/{id}/update_entry_notes/`

Attachments on lists:

- `GET /api/v1/member-lists/{id}/attachments/`
- `POST /api/v1/member-lists/{id}/attachments/`
- `DELETE /api/v1/member-lists/{id}/attachments/{attachment_id}/`

## Group Editor

The product has two different group concepts:

1. Member groups
- Domain concept for member categorization (for example teams/units).
- API: `GET/POST/PATCH/DELETE /api/v1/groups/`
- UI: `/groups`

2. Permission groups (Django auth groups)
- Security and access-control concept (permissions bundle).
- API: `GET/POST/PATCH/DELETE /api/v1/admin/groups/`
- UI: `/users` (admin section)

Use member groups for organization data and auth groups for permissions.

## Excel Export Changes

### Members export

- Endpoint: `GET /api/v1/members/export-excel/`
- New behavior: optional `columns` query parameter for explicit column selection.
- If `columns` is omitted, backend uses default member export columns.

Example:

`GET /api/v1/members/export-excel/?columns=name,lastname,email,group,departments`

### Member list export

- Endpoint: `GET /api/v1/member-lists/{id}/export-excel/`
- Supports same column selection approach via `columns=...`.
- Adds list-specific columns:
  - `list_checked`
  - `list_checked_at`
  - `list_notes`

Default list export includes member defaults plus list check/notes fields.

### Frontend behavior

The export dialog lets users choose export columns before download.
Both members and list-detail pages call the export endpoints with selected columns.

## Related References

- API overview: `docs/api/reference.md`
- Department scoping details: `docs/architecture/departments-and-permissions.md`
