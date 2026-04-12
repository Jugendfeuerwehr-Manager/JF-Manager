# API Reference

## Overview

- **Base URL**: `http://localhost:8000/api/v1/` (dev) / `https://your-domain.com/api/v1/` (prod)
- **Format**: JSON
- **Date Format**: ISO 8601 (`2025-10-01T10:30:00Z`)
- **Pagination**: All list endpoints return paginated responses

## Interactive Documentation

| Endpoint | Description |
|----------|-------------|
| `/api/docs/` | Swagger UI – browse, test, and authenticate against all endpoints |
| `/api/redoc/` | ReDoc – clean three-panel layout |
| `/api/schema/` | Raw OpenAPI 3.0 schema (JSON) for SDK generation and Postman import |

## Authentication

### JWT (Recommended for SPAs)

```bash
# Login – get tokens
POST /api/auth/login/
{"username": "user", "password": "pass"}
# → {"access": "...", "refresh": "..."}

# Use access token (valid 60 min)
Authorization: Bearer <access_token>

# Refresh (refresh token valid 7 days)
POST /api/auth/refresh/
{"refresh": "..."}
# → {"access": "new_token"}

# Verify
POST /api/auth/verify/
{"token": "..."}
```

## Pagination

All list endpoints return:

```json
{
  "count": 42,
  "next": "http://localhost:8000/api/v1/members/?page=2",
  "previous": null,
  "results": [...]
}
```

Always extract `.results` from list responses:

```typescript
const response = await api.list()
items.value = response.data.results  // ✅ Correct
items.value = response.data          // ❌ Wrong – gets the wrapper object
```

## Endpoint Reference

### Users

```
GET    /api/v1/users/me/              # Current user info
PATCH  /api/v1/users/me/              # Update profile
POST   /api/v1/users/change-password/ # Change password
```

### Members

```
GET    /api/v1/members/               # List all members
GET    /api/v1/members/{id}/          # Get single member
POST   /api/v1/members/               # Create member
PATCH  /api/v1/members/{id}/          # Update member
DELETE /api/v1/members/{id}/          # Delete member
GET    /api/v1/parents/               # List parents
```

### Inventory

```
# Items
GET    /api/v1/inventory/items/                # List items
GET    /api/v1/inventory/items/{id}/           # Get item
GET    /api/v1/inventory/items/{id}/stock/     # Item stock levels
GET    /api/v1/inventory/items/{id}/variants/  # Item variants
GET    /api/v1/inventory/items/search/?q=term  # Quick search
POST   /api/v1/inventory/items/                # Create item
PATCH  /api/v1/inventory/items/{id}/           # Update item
DELETE /api/v1/inventory/items/{id}/           # Delete item

# Categories
GET    /api/v1/inventory/categories/              # List categories
GET    /api/v1/inventory/categories/{id}/items/   # Category items
POST   /api/v1/inventory/categories/              # Create category

# Locations
GET    /api/v1/inventory/locations/               # List locations
GET    /api/v1/inventory/locations/{id}/stock/    # Location stock

# Transactions
GET    /api/v1/inventory/transactions/            # Transaction history
POST   /api/v1/inventory/transactions/            # Create transaction
GET    /api/v1/inventory/transactions/discard-statistics/  # Discard stats
```

### Qualifications

```
GET    /api/v1/qualifications/types/   # List qualification types
GET    /api/v1/qualifications/         # List qualifications
POST   /api/v1/qualifications/         # Create qualification
PATCH  /api/v1/qualifications/{id}/    # Update qualification
DELETE /api/v1/qualifications/{id}/    # Delete qualification

GET    /api/v1/specialtasks/types/     # List special task types
GET    /api/v1/specialtasks/           # List special tasks
```

### Servicebook

```
GET    /api/v1/servicebook/services/       # List services
GET    /api/v1/servicebook/services/{id}/  # Get service
POST   /api/v1/servicebook/services/       # Create service
PATCH  /api/v1/servicebook/services/{id}/  # Update service

GET    /api/v1/servicebook/attandances/    # List attendances
POST   /api/v1/servicebook/attandances/    # Create attendance
```

### Orders

```
GET    /api/v1/orders/                     # List orders
GET    /api/v1/orders/{id}/                # Get order details
POST   /api/v1/orders/                     # Create order
PATCH  /api/v1/orders/{id}/                # Update order

GET    /api/v1/order-items/                # List order items
PATCH  /api/v1/order-items/{id}/           # Update order item

GET    /api/v1/orderable-items/            # Items that can be ordered
GET    /api/v1/order-statuses/             # Available order statuses
POST   /api/v1/orders/send_summary/        # Send order summary email
```

## Query Parameters

### Filtering

Most list endpoints support filtering:

```
GET /api/v1/members/?status=active
GET /api/v1/inventory/items/?category=1
GET /api/v1/orders/?status=pending
```

### Search

```
GET /api/v1/members/?search=Max
GET /api/v1/inventory/items/search/?q=Helm
```

### Ordering

```
GET /api/v1/members/?ordering=-created_at
GET /api/v1/orders/?ordering=status,-created_at
```

### Pagination

```
GET /api/v1/members/?page=2&page_size=25
GET /api/v1/members/?limit=1000  # Override page size
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

## cURL Examples

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# List members
curl http://localhost:8000/api/v1/members/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create member
curl -X POST http://localhost:8000/api/v1/members/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Max", "last_name": "Mustermann"}'
```
