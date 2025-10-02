# JF-Manager REST API Documentation

## Overview

The JF-Manager REST API provides comprehensive access to all system resources for building modern front-end applications. This API is designed for use with Vue.js/Pinia or other modern JavaScript frameworks.

**Base URL:**
- Development: `http://localhost:8000/api/v1/`
- Production: `https://your-domain.com/api/v1/`

**API Version:** v1  
**Response Format:** JSON  
**Date Format:** ISO 8601 (e.g., `2025-10-01T10:30:00Z`)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Common Patterns](#common-patterns)
3. [API Endpoints](#api-endpoints)
   - [Users](#users)
   - [Members](#members)
   - [Inventory](#inventory)
   - [Qualifications](#qualifications)
   - [Servicebook](#servicebook)
   - [Orders](#orders)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Best Practices](#best-practices)

---

## Authentication

### JWT Authentication (Recommended for SPAs)

JWT (JSON Web Token) authentication is the recommended method for single-page applications.

#### Login

```http
POST /api/auth/login/
Content-Type: application/json

{
    "username": "your_username",
    "password": "your_password"
}
```

**Success Response (200 OK):**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Access Token:** Valid for 60 minutes  
**Refresh Token:** Valid for 7 days

#### Using the Access Token

Include the access token in the `Authorization` header for all API requests:

```http
GET /api/v1/users/me/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

#### Refresh Token

When your access token expires, use the refresh token to obtain a new one:

```http
POST /api/auth/refresh/
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Success Response (200 OK):**
```json
{
    "access": "new_access_token_here"
}
```

#### Verify Token

To verify if a token is valid:

```http
POST /api/auth/verify/
Content-Type: application/json

{
    "token": "access_token_here"
}
```

### Session Authentication

Session authentication is available for traditional web applications.

```http
POST /api/auth/login/
Cookie: sessionid=...
```

---

## Common Patterns

### Pagination

All list endpoints return paginated results by default.

**Request:**
```http
GET /api/v1/inventory/items/?page=2&page_size=50
```

**Response:**
```json
{
    "count": 150,
    "next": "http://localhost:8000/api/v1/inventory/items/?page=3",
    "previous": "http://localhost:8000/api/v1/inventory/items/?page=1",
    "results": [
        {...},
        {...}
    ]
}
```

**Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 25, max: 100)

### Filtering

Use query parameters to filter results:

```http
GET /api/v1/inventory/items/?category=1&is_variant_parent=false
```

### Search

Many endpoints support text search:

```http
GET /api/v1/inventory/items/?search=helmet
```

The search looks through multiple fields (name, description, etc.) depending on the endpoint.

### Ordering

Sort results using the `ordering` parameter:

```http
GET /api/v1/members/?ordering=-joined
```

Use `-` prefix for descending order:
- `ordering=name` → ascending by name
- `ordering=-created_at` → descending by creation date

### Nested Resources

Access nested resources through parent IDs:

```http
GET /api/v1/inventory/categories/1/items/
GET /api/v1/inventory/items/1/stock/
GET /api/v1/inventory/items/1/variants/
```

### Partial Updates

Use `PATCH` for partial updates (only send fields that change):

```http
PATCH /api/v1/members/1/
Content-Type: application/json

{
    "email": "newemail@example.com"
}
```

---

## API Endpoints

### Users

#### Get Current User

Get information about the currently authenticated user.

```http
GET /api/v1/users/me/
```

**Response (200 OK):**
```json
{
    "id": 1,
    "username": "max.mustermann",
    "email": "max@example.com",
    "first_name": "Max",
    "last_name": "Mustermann",
    "phone": "+49123456789",
    "mobile_phone": "+491234567890",
    "street": "Musterstraße 1",
    "zip_code": "12345",
    "city": "Musterstadt",
    "avatar": "http://localhost:8000/media/avatars/user1.jpg",
    "date_joined": "2023-01-01T10:00:00Z",
    "last_login": "2025-10-01T08:30:00Z",
    "is_active": true,
    "is_staff": false
}
```

#### Update Current User Profile

```http
PATCH /api/v1/users/me/
Content-Type: application/json

{
    "first_name": "Max",
    "last_name": "Mustermann",
    "email": "newemail@example.com",
    "phone": "+49123456789",
    "street": "Neue Straße 2",
    "zip_code": "54321",
    "city": "Neue Stadt"
}
```

**Editable Fields:**
- `first_name`, `last_name`
- `email`, `phone`, `mobile_phone`
- `street`, `zip_code`, `city`
- `avatar` (multipart upload)

**Response (200 OK):**
Returns the updated user object.

#### Change Password

```http
POST /api/v1/users/change-password/
Content-Type: application/json

{
    "old_password": "current_password",
    "new_password": "new_secure_password",
    "new_password_confirm": "new_secure_password"
}
```

---

### Members

#### List Members

```http
GET /api/v1/members/
```

**Query Parameters:**
- `search` - Search by name, email
- `status` - Filter by status (active, inactive, etc.)
- `ordering` - Sort by field (name, lastname, joined, birthday)

**Response (200 OK):**
```json
{
    "count": 45,
    "next": "...",
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "Max",
            "lastname": "Mustermann",
            "birthday": "2010-05-15",
            "email": "max@example.com",
            "street": "Musterstraße 1",
            "zip_code": "12345",
            "city": "Musterstadt",
            "phone": "+49123456789",
            "mobile": "+491234567890",
            "joined": "2020-01-15",
            "identityCardNumber": "ABC123456",
            "canSwimm": true,
            "status": "active",
            "notes": "Some notes",
            "parents": [
                {
                    "id": 1,
                    "name": "Peter",
                    "lastname": "Mustermann",
                    "email": "peter@example.com",
                    "phone": "+49123456789",
                    "mobile": "+491234567890"
                }
            ]
        }
    ]
}
```

#### Get Single Member

```http
GET /api/v1/members/{id}/
```

**Response (200 OK):**
Returns a single member object with full details.

#### Create Member

```http
POST /api/v1/members/
Content-Type: application/json

{
    "name": "Max",
    "lastname": "Mustermann",
    "birthday": "2010-05-15",
    "email": "max@example.com",
    "street": "Musterstraße 1",
    "zip_code": "12345",
    "city": "Musterstadt",
    "phone": "+49123456789",
    "mobile": "+491234567890",
    "joined": "2025-10-01",
    "canSwimm": true,
    "status": "active"
}
```

**Required Fields:**
- `name`, `lastname`
- `birthday`
- `joined`

**Response (201 Created):**
Returns the created member object.

#### Update Member

```http
PATCH /api/v1/members/{id}/
Content-Type: application/json

{
    "email": "newemail@example.com",
    "mobile": "+491234567890"
}
```

**Response (200 OK):**
Returns the updated member object.

#### Delete Member

```http
DELETE /api/v1/members/{id}/
```

**Response (204 No Content)**

### Parents

#### List Parents

```http
GET /api/v1/parents/
```

**Query Parameters:**
- `search` - Search by name, email
- `ordering` - Sort by field

**Response (200 OK):**
```json
{
    "count": 30,
    "results": [
        {
            "id": 1,
            "name": "Peter",
            "lastname": "Mustermann",
            "email": "peter@example.com",
            "street": "Musterstraße 1",
            "zip_code": "12345",
            "city": "Musterstadt",
            "phone": "+49123456789",
            "mobile": "+491234567890",
            "members": [1, 2]
        }
    ]
}
```

---

### Inventory

#### List Items

```http
GET /api/v1/inventory/items/
```

**Query Parameters:**
- `search` - Search by name, identifier, category name
- `category` - Filter by category ID
- `is_variant_parent` - Filter variant parents (true/false)
- `ordering` - Sort by field (name, category, created_at)

**Response (200 OK):**
```json
{
    "count": 120,
    "results": [
        {
            "id": 1,
            "name": "Feuerwehrhelm F2",
            "description": "Standardhelm für Jugendfeuerwehr",
            "category": {
                "id": 1,
                "name": "Helme",
                "item_count": 15
            },
            "identifier1": "HLM-001",
            "identifier2": "BAR-123456",
            "is_variant_parent": true,
            "has_variants": true,
            "total_stock": 45,
            "image": "http://localhost:8000/media/items/helm.jpg",
            "created_at": "2023-05-10T10:00:00Z",
            "updated_at": "2025-09-15T14:30:00Z"
        }
    ]
}
```

#### Get Single Item

```http
GET /api/v1/inventory/items/{id}/
```

**Response (200 OK):**
Returns full item details including variants if applicable.

#### Create Item

```http
POST /api/v1/inventory/items/
Content-Type: application/json

{
    "name": "Feuerwehrhelm F2",
    "description": "Standardhelm für Jugendfeuerwehr",
    "category": 1,
    "identifier1": "HLM-001",
    "is_variant_parent": false
}
```

**Required Fields:**
- `name`
- `category` (category ID)

**Response (201 Created)**

#### Get Item Stock

Get current stock levels for an item across all locations.

```http
GET /api/v1/inventory/items/{id}/stock/
```

**Response (200 OK):**
```json
{
    "total": 45,
    "rows": [
        {
            "id": 1,
            "item": 1,
            "location": {
                "id": 1,
                "name": "Hauptlager"
            },
            "quantity": 30
        },
        {
            "id": 2,
            "item": 1,
            "location": {
                "id": 2,
                "name": "Fahrzeug 1"
            },
            "quantity": 15
        }
    ]
}
```

#### Get Item Variants

```http
GET /api/v1/inventory/items/{id}/variants/
```

**Response (200 OK):**
```json
[
    {
        "id": 1,
        "parent_item": 1,
        "sku": "HLM-001-S",
        "size": "S",
        "color": "Rot",
        "attributes": {
            "weight": "1.2kg"
        },
        "total_stock": 15
    }
]
```

#### Search Items

Quick search across items:

```http
GET /api/v1/inventory/items/search/?q=helm
```

**Response (200 OK):**
```json
{
    "results": [
        {...}
    ]
}
```

#### List Categories

```http
GET /api/v1/inventory/categories/
```

**Response (200 OK):**
```json
{
    "count": 10,
    "results": [
        {
            "id": 1,
            "name": "Helme",
            "description": "Feuerwehrhelme",
            "item_count": 15,
            "parent": null,
            "created_at": "2023-01-01T10:00:00Z"
        }
    ]
}
```

#### Get Category Items

Get all items in a specific category:

```http
GET /api/v1/inventory/categories/{id}/items/
```

#### List Storage Locations

```http
GET /api/v1/inventory/locations/
```

**Query Parameters:**
- `search` - Search by name, member name
- `is_member` - Filter member locations (true/false)
- `parent` - Filter by parent location ID

**Response (200 OK):**
```json
{
    "count": 20,
    "results": [
        {
            "id": 1,
            "name": "Hauptlager",
            "description": "Zentrales Lager",
            "parent": null,
            "is_member": false,
            "member": null,
            "address": "Feuerwehrhaus",
            "total_items": 150
        }
    ]
}
```

#### Get Location Stock

```http
GET /api/v1/inventory/locations/{id}/stock/
```

**Response (200 OK):**
```json
{
    "total": 150,
    "rows": [
        {
            "id": 1,
            "item": {
                "id": 1,
                "name": "Feuerwehrhelm F2"
            },
            "location": 1,
            "quantity": 30
        }
    ]
}
```

#### List Transactions

Get inventory transaction history:

```http
GET /api/v1/inventory/transactions/
```

**Query Parameters:**
- `transaction_type` - Filter by type (in, out, transfer, adjustment)
- `item` - Filter by item ID
- `source` - Filter by source location
- `target` - Filter by target location
- `ordering` - Sort by field (default: -created_at)

**Response (200 OK):**
```json
{
    "count": 500,
    "results": [
        {
            "id": 1,
            "transaction_type": "transfer",
            "item": {
                "id": 1,
                "name": "Feuerwehrhelm F2"
            },
            "item_variant": null,
            "source": {
                "id": 1,
                "name": "Hauptlager"
            },
            "target": {
                "id": 2,
                "name": "Fahrzeug 1"
            },
            "quantity": 5,
            "note": "Fahrzeugbestückung",
            "user": {
                "id": 1,
                "username": "admin",
                "full_name": "Admin User"
            },
            "created_at": "2025-10-01T10:30:00Z"
        }
    ]
}
```

---

### Qualifications

#### List Qualification Types

```http
GET /api/v1/qualifications/types/
```

**Query Parameters:**
- `is_active` - Filter active types (true/false)
- `category` - Filter by category
- `search` - Search by name, description
- `ordering` - Sort by field

**Response (200 OK):**
```json
{
    "count": 25,
    "results": [
        {
            "id": 1,
            "name": "Truppmann 1",
            "description": "Grundausbildung",
            "category": "grundausbildung",
            "validity_months": 0,
            "is_active": true,
            "created_at": "2023-01-01T10:00:00Z"
        }
    ]
}
```

#### List Qualifications

```http
GET /api/v1/qualifications/
```

**Query Parameters:**
- `member` - Filter by member ID
- `user` - Filter by user ID
- `type` - Filter by qualification type ID
- `search` - Search by member/user name, type name
- `ordering` - Sort by field (default: -date_acquired)

**Response (200 OK):**
```json
{
    "count": 150,
    "results": [
        {
            "id": 1,
            "member": {
                "id": 1,
                "name": "Max",
                "lastname": "Mustermann"
            },
            "user": null,
            "type": {
                "id": 1,
                "name": "Truppmann 1"
            },
            "date_acquired": "2024-03-15",
            "date_expires": null,
            "is_expired": false,
            "certificate_number": "TM1-2024-001",
            "notes": "Erfolgreich abgeschlossen",
            "created_at": "2024-03-15T10:00:00Z"
        }
    ]
}
```

#### Create Qualification

```http
POST /api/v1/qualifications/
Content-Type: application/json

{
    "member": 1,
    "type": 1,
    "date_acquired": "2025-10-01",
    "certificate_number": "TM1-2025-001"
}
```

**Required Fields:**
- `member` OR `user` (one must be provided)
- `type` (qualification type ID)
- `date_acquired`

**Response (201 Created)**

#### Special Tasks

Similar endpoints for special tasks:

```http
GET /api/v1/specialtasks/types/
GET /api/v1/specialtasks/
POST /api/v1/specialtasks/
```

---

### Servicebook

#### List Services

```http
GET /api/v1/servicebook/services/
```

**Query Parameters:**
- `search` - Search by title, description
- `ordering` - Sort by field (default: -date)

**Response (200 OK):**
```json
{
    "count": 80,
    "results": [
        {
            "id": 1,
            "title": "Übungsdienst",
            "description": "Wöchentlicher Übungsdienst",
            "date": "2025-10-01",
            "start_time": "18:00:00",
            "end_time": "20:00:00",
            "location": "Feuerwehrhaus",
            "service_type": "training",
            "attendee_count": 15,
            "created_at": "2025-09-25T10:00:00Z"
        }
    ]
}
```

#### Create Service

```http
POST /api/v1/servicebook/services/
Content-Type: application/json

{
    "title": "Übungsdienst",
    "description": "Wöchentlicher Übungsdienst",
    "date": "2025-10-15",
    "start_time": "18:00:00",
    "end_time": "20:00:00",
    "location": "Feuerwehrhaus",
    "service_type": "training"
}
```

**Required Fields:**
- `title`
- `date`
- `start_time`, `end_time`

**Response (201 Created)**

#### List Attendances

```http
GET /api/v1/servicebook/attandances/
```

**Query Parameters:**
- `service` - Filter by service ID
- `member` - Filter by member ID

**Response (200 OK):**
```json
{
    "count": 200,
    "results": [
        {
            "id": 1,
            "service": 1,
            "member": {
                "id": 1,
                "name": "Max",
                "lastname": "Mustermann"
            },
            "attended": true,
            "excused": false,
            "notes": ""
        }
    ]
}
```

---

### Orders

#### List Orders

```http
GET /api/v1/orders/
```

**Query Parameters:**
- `search` - Search by member name, order number
- `status` - Filter by status code
- `ordering` - Sort by field (default: -created_at)

**Response (200 OK):**
```json
{
    "count": 50,
    "results": [
        {
            "id": 1,
            "order_number": "ORD-2025-001",
            "member": {
                "id": 1,
                "name": "Max",
                "lastname": "Mustermann"
            },
            "ordered_by": {
                "id": 1,
                "username": "admin"
            },
            "status": {
                "code": "NEW",
                "name": "Neu"
            },
            "total_items": 3,
            "notes": "Dringend",
            "created_at": "2025-09-28T10:00:00Z",
            "updated_at": "2025-09-28T10:00:00Z"
        }
    ]
}
```

#### Get Single Order

```http
GET /api/v1/orders/{id}/
```

**Response (200 OK):**
```json
{
    "id": 1,
    "order_number": "ORD-2025-001",
    "member": {...},
    "ordered_by": {...},
    "status": {...},
    "items": [
        {
            "id": 1,
            "item": {
                "id": 5,
                "name": "T-Shirt Jugendfeuerwehr"
            },
            "variant": {
                "id": 10,
                "sku": "TSHIRT-M-BLUE",
                "size": "M",
                "color": "Blau"
            },
            "quantity": 2,
            "status": {
                "code": "ORDERED",
                "name": "Bestellt"
            }
        }
    ],
    "notes": "Dringend",
    "created_at": "2025-09-28T10:00:00Z",
    "updated_at": "2025-09-28T10:00:00Z"
}
```

#### Create Order

```http
POST /api/v1/orders/
Content-Type: application/json

{
    "member": 1,
    "notes": "Dringend",
    "items": [
        {
            "item": 5,
            "variant": 10,
            "quantity": 2
        }
    ]
}
```

**Required Fields:**
- `member` (member ID)
- `items` (array of order items)

**Response (201 Created)**

#### List Orderable Items

```http
GET /api/v1/orders/orderable-items/
```

Returns items that can be ordered.

#### List Order Statuses

```http
GET /api/v1/orders/statuses/
```

Returns available order statuses:

```json
{
    "count": 5,
    "results": [
        {
            "id": 1,
            "code": "NEW",
            "name": "Neu",
            "description": "Neue Bestellung"
        },
        {
            "id": 2,
            "code": "ORDERED",
            "name": "Bestellt",
            "description": "Bei Lieferant bestellt"
        },
        {
            "id": 3,
            "code": "DELIVERED",
            "name": "Geliefert",
            "description": "An Mitglied ausgeliefert"
        }
    ]
}
```

---

## Error Handling

### Error Response Format

All errors return a consistent JSON structure:

```json
{
    "detail": "Error message here"
}
```

Or for validation errors:

```json
{
    "field_name": [
        "Error message for this field"
    ],
    "another_field": [
        "Error message for this field"
    ]
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | OK - Request succeeded |
| 201 | Created - Resource created successfully |
| 204 | No Content - Resource deleted successfully |
| 400 | Bad Request - Invalid data provided |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Permission denied |
| 404 | Not Found - Resource doesn't exist |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |

### Common Error Scenarios

**Authentication Failed:**
```json
{
    "detail": "Authentication credentials were not provided."
}
```

**Permission Denied:**
```json
{
    "detail": "You do not have permission to perform this action."
}
```

**Resource Not Found:**
```json
{
    "detail": "Not found."
}
```

**Validation Error:**
```json
{
    "name": ["This field is required."],
    "email": ["Enter a valid email address."]
}
```

---

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Authenticated Users:** 1000 requests per hour
- **Unauthenticated:** 100 requests per hour

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1696147200
```

---

## Best Practices

### 1. Use JWT for SPAs

For Vue.js applications, use JWT authentication:

```javascript
// Example with Pinia store
export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: null,
    refreshToken: null,
    user: null
  }),
  
  actions: {
    async login(username, password) {
      const response = await fetch('/api/auth/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      const data = await response.json();
      this.accessToken = data.access;
      this.refreshToken = data.refresh;
      
      // Fetch user data
      await this.fetchUser();
    },
    
    async fetchUser() {
      const response = await fetch('/api/v1/users/me/', {
        headers: { 
          'Authorization': `Bearer ${this.accessToken}` 
        }
      });
      
      this.user = await response.json();
    }
  }
});
```

### 2. Handle Token Refresh

Automatically refresh tokens before they expire:

```javascript
// Axios interceptor example
axios.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // Try to refresh token
      const authStore = useAuthStore();
      await authStore.refreshAccessToken();
      
      // Retry original request
      return axios(error.config);
    }
    return Promise.reject(error);
  }
);
```

### 3. Use Pagination Efficiently

Implement infinite scrolling or "Load More":

```javascript
const items = ref([]);
const nextPage = ref(null);

async function loadMore() {
  const url = nextPage.value || '/api/v1/inventory/items/';
  const response = await fetch(url, {
    headers: { 'Authorization': `Bearer ${accessToken}` }
  });
  
  const data = await response.json();
  items.value.push(...data.results);
  nextPage.value = data.next;
}
```

### 4. Optimize with Field Selection

Request only needed fields to reduce payload size:

```http
GET /api/v1/members/?fields=id,name,lastname,email
```

### 5. Use Partial Updates

Use PATCH instead of PUT to update only changed fields:

```javascript
// Only send changed fields
await fetch(`/api/v1/members/${id}/`, {
  method: 'PATCH',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${accessToken}`
  },
  body: JSON.stringify({ 
    email: 'newemail@example.com'  // Only this field
  })
});
```

### 6. Implement Optimistic Updates

Update UI immediately, then sync with server:

```javascript
// Update UI immediately
member.email = newEmail;

// Then sync with server
try {
  await updateMember(member.id, { email: newEmail });
} catch (error) {
  // Revert on error
  member.email = oldEmail;
  showError('Update failed');
}
```

### 7. Cache Static Data

Cache frequently accessed, rarely changing data:

```javascript
// Cache qualification types
const qualificationTypesStore = defineStore('qualificationTypes', {
  state: () => ({
    types: [],
    lastFetched: null
  }),
  
  actions: {
    async fetchTypes() {
      // Only fetch if cache is older than 1 hour
      if (this.lastFetched && Date.now() - this.lastFetched < 3600000) {
        return this.types;
      }
      
      const response = await fetch('/api/v1/qualifications/types/');
      this.types = await response.json();
      this.lastFetched = Date.now();
      
      return this.types;
    }
  }
});
```

### 8. Handle Errors Gracefully

Provide user-friendly error messages:

```javascript
async function createMember(memberData) {
  try {
    const response = await fetch('/api/v1/members/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify(memberData)
    });
    
    if (!response.ok) {
      const errors = await response.json();
      throw new ValidationError(errors);
    }
    
    return await response.json();
  } catch (error) {
    if (error instanceof ValidationError) {
      // Show field-specific errors
      showValidationErrors(error.errors);
    } else {
      // Show generic error
      showError('Mitglied konnte nicht erstellt werden');
    }
  }
}
```

---

## Vue.js Integration Example

### Complete Pinia Store Example

```javascript
// stores/members.js
import { defineStore } from 'pinia';
import { useAuthStore } from './auth';

export const useMembersStore = defineStore('members', {
  state: () => ({
    members: [],
    currentMember: null,
    loading: false,
    error: null,
    pagination: {
      count: 0,
      next: null,
      previous: null
    }
  }),
  
  getters: {
    activeMembersCount: (state) => {
      return state.members.filter(m => m.status === 'active').length;
    }
  },
  
  actions: {
    async fetchMembers(page = 1, filters = {}) {
      this.loading = true;
      this.error = null;
      
      const authStore = useAuthStore();
      const params = new URLSearchParams({
        page,
        ...filters
      });
      
      try {
        const response = await fetch(`/api/v1/members/?${params}`, {
          headers: {
            'Authorization': `Bearer ${authStore.accessToken}`
          }
        });
        
        if (!response.ok) throw new Error('Failed to fetch members');
        
        const data = await response.json();
        this.members = data.results;
        this.pagination = {
          count: data.count,
          next: data.next,
          previous: data.previous
        };
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },
    
    async fetchMember(id) {
      this.loading = true;
      const authStore = useAuthStore();
      
      try {
        const response = await fetch(`/api/v1/members/${id}/`, {
          headers: {
            'Authorization': `Bearer ${authStore.accessToken}`
          }
        });
        
        if (!response.ok) throw new Error('Member not found');
        
        this.currentMember = await response.json();
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },
    
    async createMember(memberData) {
      const authStore = useAuthStore();
      
      const response = await fetch('/api/v1/members/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.accessToken}`
        },
        body: JSON.stringify(memberData)
      });
      
      if (!response.ok) {
        const errors = await response.json();
        throw errors;
      }
      
      const newMember = await response.json();
      this.members.push(newMember);
      return newMember;
    },
    
    async updateMember(id, updates) {
      const authStore = useAuthStore();
      
      const response = await fetch(`/api/v1/members/${id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authStore.accessToken}`
        },
        body: JSON.stringify(updates)
      });
      
      if (!response.ok) {
        const errors = await response.json();
        throw errors;
      }
      
      const updatedMember = await response.json();
      
      // Update in local state
      const index = this.members.findIndex(m => m.id === id);
      if (index !== -1) {
        this.members[index] = updatedMember;
      }
      
      if (this.currentMember?.id === id) {
        this.currentMember = updatedMember;
      }
      
      return updatedMember;
    },
    
    async deleteMember(id) {
      const authStore = useAuthStore();
      
      const response = await fetch(`/api/v1/members/${id}/`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${authStore.accessToken}`
        }
      });
      
      if (!response.ok) throw new Error('Failed to delete member');
      
      // Remove from local state
      this.members = this.members.filter(m => m.id !== id);
      if (this.currentMember?.id === id) {
        this.currentMember = null;
      }
    }
  }
});
```

---

## Support

For questions or issues with the API:

- **Email:** support@jf-manager.example
- **GitHub Issues:** https://github.com/Jugendfeuerwehr-Manager/JF-Manager/issues
- **Documentation:** https://docs.jf-manager.example

---

**Last Updated:** October 1, 2025  
**API Version:** 1.0
