# JF-Manager REST API Quick Reference

## Authentication

### Login
```bash
POST /api/auth/login/
{
  "username": "user",
  "password": "pass"
}
```

### Use Token
```bash
Authorization: Bearer <token>
```

---

## Quick Endpoint Reference

### Users
```bash
GET    /api/v1/users/me/              # Current user info
PATCH  /api/v1/users/me/              # Update profile
POST   /api/v1/users/change-password/ # Change password
```

### Members
```bash
GET    /api/v1/members/               # List all members
GET    /api/v1/members/{id}/          # Get single member
POST   /api/v1/members/               # Create member
PATCH  /api/v1/members/{id}/          # Update member
DELETE /api/v1/members/{id}/          # Delete member

GET    /api/v1/parents/               # List parents
```

### Inventory
```bash
# Items
GET    /api/v1/inventory/items/              # List items
GET    /api/v1/inventory/items/{id}/         # Get item
GET    /api/v1/inventory/items/{id}/stock/   # Item stock levels
GET    /api/v1/inventory/items/{id}/variants/# Item variants
GET    /api/v1/inventory/items/search/?q=term # Quick search
POST   /api/v1/inventory/items/              # Create item
PATCH  /api/v1/inventory/items/{id}/         # Update item
DELETE /api/v1/inventory/items/{id}/         # Delete item

# Categories
GET    /api/v1/inventory/categories/         # List categories
GET    /api/v1/inventory/categories/{id}/items/ # Category items
POST   /api/v1/inventory/categories/         # Create category

# Locations
GET    /api/v1/inventory/locations/          # List locations
GET    /api/v1/inventory/locations/{id}/stock/ # Location stock

# Transactions
GET    /api/v1/inventory/transactions/       # Transaction history
POST   /api/v1/inventory/transactions/       # Create transaction
```

### Qualifications
```bash
GET    /api/v1/qualifications/types/   # List qualification types
GET    /api/v1/qualifications/          # List qualifications
POST   /api/v1/qualifications/          # Create qualification
PATCH  /api/v1/qualifications/{id}/     # Update qualification
DELETE /api/v1/qualifications/{id}/     # Delete qualification

GET    /api/v1/specialtasks/types/      # List special task types
GET    /api/v1/specialtasks/            # List special tasks
```

### Servicebook
```bash
GET    /api/v1/servicebook/services/    # List services
GET    /api/v1/servicebook/services/{id}/ # Get service
POST   /api/v1/servicebook/services/    # Create service
PATCH  /api/v1/servicebook/services/{id}/ # Update service

GET    /api/v1/servicebook/attandances/ # List attendances
POST   /api/v1/servicebook/attandances/ # Create attendance
```

### Orders
```bash
GET    /api/v1/orders/                  # List orders
GET    /api/v1/orders/{id}/             # Get order details
POST   /api/v1/orders/                  # Create order
PATCH  /api/v1/orders/{id}/             # Update order

GET    /api/v1/orders/orderable-items/  # Items that can be ordered
GET    /api/v1/orders/statuses/         # Available order statuses
```

---

## Common Query Parameters

### Pagination
```bash
?page=2&page_size=50
```

### Search
```bash
?search=helmut
```

### Filtering
```bash
?category=1&is_active=true
```

### Ordering
```bash
?ordering=-created_at    # Descending
?ordering=name           # Ascending
```

### Multiple Filters
```bash
?search=helm&category=1&ordering=-created_at&page=1
```

---

## Response Format

### List Response
```json
{
  "count": 100,
  "next": "http://.../?page=2",
  "previous": null,
  "results": [...]
}
```

### Error Response
```json
{
  "detail": "Error message"
}
```

Or for validation:
```json
{
  "field_name": ["Error message"]
}
```

---

## Status Codes

- `200` OK
- `201` Created
- `204` No Content
- `400` Bad Request
- `401` Unauthorized
- `403` Forbidden
- `404` Not Found
- `500` Server Error

---

## Vue.js Example

```javascript
// Pinia Store
export const useMembersStore = defineStore('members', {
  state: () => ({
    members: [],
    loading: false
  }),
  
  actions: {
    async fetchMembers() {
      this.loading = true;
      const authStore = useAuthStore();
      
      const response = await fetch('/api/v1/members/', {
        headers: {
          'Authorization': `Bearer ${authStore.accessToken}`
        }
      });
      
      const data = await response.json();
      this.members = data.results;
      this.loading = false;
    }
  }
});

// Component
const membersStore = useMembersStore();
await membersStore.fetchMembers();
```

---

## cURL Examples

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### Get Members
```bash
curl http://localhost:8000/api/v1/members/ \
  -H "Authorization: Bearer <your-token>"
```

### Create Member
```bash
curl -X POST http://localhost:8000/api/v1/members/ \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Max",
    "lastname":"Mustermann",
    "birthday":"2010-05-15",
    "joined":"2025-10-01"
  }'
```

### Update Member
```bash
curl -X PATCH http://localhost:8000/api/v1/members/1/ \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"email":"newemail@example.com"}'
```

---

For full documentation, see: `API_DOCUMENTATION_ENHANCED.md`
