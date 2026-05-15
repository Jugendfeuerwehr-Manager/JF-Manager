# API Reference

## Overview

- Base URL: `http://localhost:8000/api/v1/` (dev) / `https://your-domain.com/api/v1/` (prod)
- Format: JSON
- Date format: ISO 8601 (`2025-10-01T10:30:00Z`)
- Authentication: JWT Bearer
- Pagination: list endpoints return `count/next/previous/results`

## Interactive Documentation

| Endpoint | Description |
|----------|-------------|
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | OpenAPI schema |

## Authentication

```bash
POST /api/auth/login/
{"username": "user", "password": "pass"}
# -> {"access": "...", "refresh": "..."}

POST /api/auth/refresh/
{"refresh": "..."}
# -> {"access": "..."}
```

OIDC (SSO) flow endpoints:

- `GET /api/v1/auth/oidc/public-config/`
- `GET /api/v1/auth/oidc/login/`
- `GET /api/v1/auth/oidc/callback/`
- `POST /api/v1/auth/oidc/exchange/`

## Pagination

Example list response:

```json
{
  "count": 42,
  "next": "http://localhost:8000/api/v1/members/?page=2",
  "previous": null,
  "results": []
}
```

Frontend note:

```typescript
const response = await api.list()
items.value = response.data.results
```

## Endpoint Groups

### Users And Admin

```
GET    /api/v1/users/me/
PATCH  /api/v1/users/me/
POST   /api/v1/users/change-password/

GET    /api/v1/admin/users/
POST   /api/v1/admin/users/
PATCH  /api/v1/admin/users/{id}/
DELETE /api/v1/admin/users/{id}/

GET    /api/v1/admin/groups/
POST   /api/v1/admin/groups/
PATCH  /api/v1/admin/groups/{id}/
DELETE /api/v1/admin/groups/{id}/

GET    /api/v1/admin/permissions/
```

### Members, Groups, Parents

```
GET    /api/v1/members/
GET    /api/v1/members/{id}/
POST   /api/v1/members/
PATCH  /api/v1/members/{id}/
DELETE /api/v1/members/{id}/
GET    /api/v1/members/statistics/
GET    /api/v1/members/export-excel/

GET    /api/v1/groups/
POST   /api/v1/groups/
PATCH  /api/v1/groups/{id}/
DELETE /api/v1/groups/{id}/

GET    /api/v1/parents/
POST   /api/v1/parents/
PATCH  /api/v1/parents/{id}/
DELETE /api/v1/parents/{id}/

GET    /api/v1/statuses/
GET    /api/v1/events/
GET    /api/v1/event-types/
```

### Member Lists

```
GET    /api/v1/member-lists/
GET    /api/v1/member-lists/{id}/
POST   /api/v1/member-lists/
PATCH  /api/v1/member-lists/{id}/
DELETE /api/v1/member-lists/{id}/

POST   /api/v1/member-lists/{id}/add_member/
POST   /api/v1/member-lists/{id}/remove_member/
POST   /api/v1/member-lists/{id}/bulk_add/

POST   /api/v1/member-lists/{id}/toggle_check/
POST   /api/v1/member-lists/{id}/set_check/
POST   /api/v1/member-lists/{id}/check_all/
POST   /api/v1/member-lists/{id}/uncheck_all/
PATCH  /api/v1/member-lists/{id}/update_entry_notes/

GET    /api/v1/member-lists/{id}/attachments/
POST   /api/v1/member-lists/{id}/attachments/
DELETE /api/v1/member-lists/{id}/attachments/{attachment_id}/

GET    /api/v1/member-lists/{id}/export-excel/
```

### Departments

```
GET    /api/v1/departments/
POST   /api/v1/departments/
PATCH  /api/v1/departments/{id}/
DELETE /api/v1/departments/{id}/

GET    /api/v1/admin/department-roles/
POST   /api/v1/admin/department-roles/
PATCH  /api/v1/admin/department-roles/{id}/
DELETE /api/v1/admin/department-roles/{id}/
```

### Settings, LDAP, OIDC

```
GET    /api/v1/settings/
GET    /api/v1/settings/permissions/

GET    /api/v1/settings/general/
PATCH  /api/v1/settings/general/
GET    /api/v1/settings/email/
PATCH  /api/v1/settings/email/
GET    /api/v1/settings/member/
PATCH  /api/v1/settings/member/
GET    /api/v1/settings/service/
PATCH  /api/v1/settings/service/
GET    /api/v1/settings/order/
PATCH  /api/v1/settings/order/
GET    /api/v1/settings/ldap/
PATCH  /api/v1/settings/ldap/
GET    /api/v1/settings/oidc/
PATCH  /api/v1/settings/oidc/

POST   /api/v1/settings/ldap/test-connection/
POST   /api/v1/settings/ldap/browse/
POST   /api/v1/settings/oidc/test-discovery/

GET    /api/v1/ldap-department-mappings/
POST   /api/v1/ldap-department-mappings/
DELETE /api/v1/ldap-department-mappings/{id}/

GET    /api/v1/oidc-group-mappings/
POST   /api/v1/oidc-group-mappings/
DELETE /api/v1/oidc-group-mappings/{id}/
```

### External Sync

```
GET    /api/v1/sync-jobs/
POST   /api/v1/sync-jobs/
PATCH  /api/v1/sync-jobs/{id}/
DELETE /api/v1/sync-jobs/{id}/

POST   /api/v1/sync-jobs/{id}/test_connection/
POST   /api/v1/sync-jobs/{id}/run_now/
GET    /api/v1/sync-jobs/{id}/garbage-collection-preview/
POST   /api/v1/sync-jobs/{id}/garbage-collect/

POST   /api/v1/sync-jobs/spond-top-level-groups/
GET    /api/v1/sync-runs/
```

### Inventory

```
GET    /api/v1/inventory/items/
GET    /api/v1/inventory/items/{id}/
GET    /api/v1/inventory/items/{id}/stock/
GET    /api/v1/inventory/items/{id}/variants/
GET    /api/v1/inventory/items/search/?q=term
POST   /api/v1/inventory/items/
PATCH  /api/v1/inventory/items/{id}/
DELETE /api/v1/inventory/items/{id}/

GET    /api/v1/inventory/categories/
GET    /api/v1/inventory/categories/{id}/items/
POST   /api/v1/inventory/categories/

GET    /api/v1/inventory/locations/
GET    /api/v1/inventory/locations/{id}/stock/

GET    /api/v1/inventory/transactions/
POST   /api/v1/inventory/transactions/
GET    /api/v1/inventory/transactions/discard-statistics/
```

### Servicebook

```
GET    /api/v1/servicebook/services/
GET    /api/v1/servicebook/services/{id}/
POST   /api/v1/servicebook/services/
PATCH  /api/v1/servicebook/services/{id}/
DELETE /api/v1/servicebook/services/{id}/

GET    /api/v1/servicebook/attendances/
POST   /api/v1/servicebook/attendances/
PATCH  /api/v1/servicebook/attendances/{id}/
DELETE /api/v1/servicebook/attendances/{id}/
```

### Orders

```
GET    /api/v1/orders/
GET    /api/v1/orders/{id}/
POST   /api/v1/orders/
PATCH  /api/v1/orders/{id}/
DELETE /api/v1/orders/{id}/

GET    /api/v1/order-items/
PATCH  /api/v1/order-items/{id}/

GET    /api/v1/orderable-items/
GET    /api/v1/order-statuses/
POST   /api/v1/orders/send_summary/
```

### Qualifications

```
GET    /api/v1/qualifications/types/
GET    /api/v1/qualifications/
POST   /api/v1/qualifications/
PATCH  /api/v1/qualifications/{id}/
DELETE /api/v1/qualifications/{id}/

GET    /api/v1/qualifications/specialtask-types/
GET    /api/v1/qualifications/specialtasks/
POST   /api/v1/qualifications/specialtasks/
PATCH  /api/v1/qualifications/specialtasks/{id}/
DELETE /api/v1/qualifications/specialtasks/{id}/
```

## Query Parameters

Common patterns:

```bash
# Filtering
GET /api/v1/members/?status=1&group=2

# Search
GET /api/v1/members/?search=Max

# Ordering
GET /api/v1/members/?ordering=-created_at

# Pagination
GET /api/v1/members/?page=2&page_size=25
GET /api/v1/members/?limit=1000
```

## Error Responses

### 400 Bad Request

```json
{
  "field_name": ["Error message"],
  "non_field_errors": ["General error"]
}
```

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden

```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found

```json
{
  "detail": "Not found."
}
```
