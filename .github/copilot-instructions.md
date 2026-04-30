# JF-Manager AI Agent Instructions

## Project Overview

**JF-Manager** is a Youth Fire Brigade (Jugendfeuerwehr) management system with a Django REST backend and Vue 3 SPA frontend. Started in 2018 as an internal tool, open-sourced in 2025. Manages members, inventory, orders, qualifications, and service books.

## Tech Stack

- **Backend**: Django 5.0 + DRF + PostgreSQL/SQLite
- **Frontend**: Vue 3 + TypeScript + Pinia + PrimeVue + Vite
- **Auth**: JWT (djangorestframework-simplejwt)
- **State**: Pinia stores (Composition API pattern)
- **Components**: PrimeVue UI library

## Critical Architecture Patterns

### 1. Django App Structure - Modular API Pattern

The backend uses a **modern modular API architecture** separate from legacy Django views:

```
backend/{app}/
├── api/                    # NEW: REST API (use this)
│   ├── serializers/       # Domain-specific serializers
│   ├── viewsets/          # DRF ViewSets with actions
│   ├── filters.py         # django-filter classes
│   └── permissions.py     # Custom DRF permissions
├── views.py               # LEGACY: Django template views (deprecating)
├── models/                # Django models (unchanged)
└── notifications/         # Business logic services (orders app)
```

**Key Rule**: All new API development goes in `api/` subdirectory, not root `views.py`. The `orders` app exemplifies this pattern perfectly (see `backend/orders/api/`).

### 2. Frontend Architecture - Atomic Design + Pinia

```
frontend/src/
├── types/orders.ts              # All TypeScript interfaces (20-30 per domain)
├── api/orders.ts                # HTTP client (uses axios instance)
├── stores/orders.ts             # Pinia store (Composition API)
└── components/orders/
    ├── atoms/                   # Single-purpose (OrderStatusBadge)
    ├── molecules/               # Composed features (OrderCard)
    └── organisms/               # Complex state-aware (OrdersList)
```

**Critical Pattern**: Components are **presentation-only**. All business logic lives in Pinia stores using Composition API with `defineStore(() => {})` pattern.

### 3. Django REST Framework Pagination

**ALL** list endpoints return paginated responses:

```typescript
// Backend returns:
{ count: 5, next: null, previous: null, results: [...] }

// Frontend must extract .results:
const response = await api.list()
items.value = response.data.results  // ✅ Correct
items.value = response.data           // ❌ Wrong
```

**Type**: Always use `PaginatedResponse<T>` for list endpoints (see `frontend/src/types/orders.ts`).

### 4. Pinia Store Pattern (Composition API)

```typescript
export const useOrdersStore = defineStore('orders', () => {
  // State - use ref()
  const orders = ref<Order[]>([])
  const loading = ref(false)
  
  // Computed - use computed()
  const hasOrders = computed(() => orders.value.length > 0)
  
  // Actions - async functions
  async function fetchOrders(params?: OrderListParams) {
    loading.value = true
    try {
      const response = await ordersApi.list(params)
      orders.value = response.data.results  // Extract .results!
      return orders.value
    } finally {
      loading.value = false
    }
  }
  
  return { orders, loading, hasOrders, fetchOrders }
})
```

**Never** mutate store state from components - call store actions.

## Development Workflow

### Local Development Setup

```bash
# Start both servers
./start-dev.sh

# Or manually:
# Backend (from backend/)
pipenv install
pipenv run python manage.py migrate
pipenv run python manage.py runserver

# Frontend (from frontend/)
npm install
npm run dev
```

**Ports**: Backend on `:8000`, Frontend on `:5173`

### Critical Environment Variables

```bash
# Backend (.env or docker-compose)
DJANGO_SECRET_KEY=your-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3  # or postgres://
REDIS_URL=none  # optional

# Frontend (frontend/.env)
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### API URL Structure

```
/api/v1/
  ├── orders/              # Order management
  ├── order-items/         # Individual order items
  ├── orderable-items/     # Product catalog
  ├── order-statuses/      # Status workflow
  ├── members/             # Member management
  ├── parents/             # Parent contacts
  ├── inventory/items/     # Inventory system
  └── users/me/            # Current user
```

**Important**: ViewSets are registered in `backend/jf_manager_backend/rest_urls.py`, not individual app URLs.

## Project-Specific Conventions

### 1. Component Props/Emits Pattern

```vue
<script setup lang="ts">
// Props with interface
interface Props {
  orderId?: number
  initialData?: Order
}
const props = defineProps<Props>()

// Emits with typed events
const emit = defineEmits<{
  success: [orderId: number]
  error: [error: unknown]
}>()
</script>
```

### 2. API Client Pattern

All API clients follow this structure:

```typescript
// api/orders.ts
import apiClient from './index'  // Axios instance with auth
import type { Order, PaginatedResponse } from '@/types/orders'

export const ordersApi = {
  list(params?: OrderListParams) {
    return apiClient.get<PaginatedResponse<Order>>('/orders/', { params })
  },
  get(id: number) {
    return apiClient.get<Order>(`/orders/${id}/`)
  },
  create(data: OrderCreate) {
    return apiClient.post<Order>('/orders/', data)
  }
}
```

The `apiClient` (from `api/index.ts`) handles JWT auth, token refresh, and CORS automatically.

### 3. ViewSet Custom Actions Pattern

```python
@action(detail=False, methods=['post'])
def send_summary(self, request):
    """Custom endpoint: POST /api/v1/orders/send_summary/"""
    # Business logic here
    return Response({'success': True})
```

Custom actions become new endpoints automatically. Use `detail=True` for `/orders/{id}/action/`, `detail=False` for `/orders/action/`.

### 4. Serializer Selection Pattern

```python
def get_serializer_class(self):
    """Use different serializers per action"""
    if self.action == 'list':
        return OrderListSerializer      # Minimal fields
    elif self.action == 'create':
        return OrderCreateSerializer    # Validation rules
    return OrderDetailSerializer        # Full fields
```

This pattern is used extensively in `orders`, `members`, and `inventory` apps.

### 5. Status Workflow Pattern (Orders Domain)

Orders use a service-based workflow system:

```python
# backend/orders/notifications/workflow_service.py
from orders.notifications import OrderWorkflowService

# Get allowed next statuses
next_statuses = OrderWorkflowService.get_available_transitions(current_status)

# Validate transition
is_valid = OrderWorkflowService.validate_status_change(old_status, new_status)
```

**Never** change order status without validation via `OrderWorkflowService`.

## Common Pitfalls & Solutions

### ❌ Pitfall: Using Legacy Views

```python
# DON'T add to backend/orders/views.py
def my_new_endpoint(request):
    pass
```

✅ **DO**: Add to `backend/orders/api/viewsets/`

### ❌ Pitfall: Forgetting .results Extraction

```typescript
// DON'T
const response = await api.list()
items.value = response.data  // Sets to { count, next, previous, results }
```

✅ **DO**: `items.value = response.data.results`

### ❌ Pitfall: Mutating Store State from Components

```vue
// DON'T
ordersStore.orders.push(newOrder)
```

✅ **DO**: Create store action `addOrder(order)` and call it

### ❌ Pitfall: Using Mock Data in Components

The `OrderFormView.vue` bug (see `ORDER_BUGFIX_2025_01_04.md`) shows the pattern:

```typescript
// DON'T
const members = ref([{ id: 1, full_name: 'Mock User' }])

// DO
const membersStore = useMembersStore()
const members = computed(() => membersStore.members)
onMounted(() => membersStore.fetchMembers({ limit: 1000 }))
```

Always fetch real data via stores.

## Testing & Debugging

### Backend API Tests

```bash
cd backend
pipenv run python run_api_tests.py
```

Tests are in `backend/api_tests/`. The OpenAPI spec is in `backend/schema.yml` (regenerate with `manage.py spectacular --file schema.yml`).

### Frontend Dev Tools

- Vue DevTools browser extension (essential)
- Check `backend.log` for Django errors
- Network tab: All API calls show JWT auth headers

### Common Debug Commands

```bash
# Backend logs
tail -f backend.log

# Check migrations
cd backend && pipenv run python manage.py showmigrations

# Django shell
pipenv run python manage.py shell

# Type check frontend
cd frontend && npm run type-check
```

## Documentation References

**In-Repo Docs** (read these for context):
- `docs/architecture/backend-structure.md` - Backend app layout, permissions, how to add an endpoint
- `docs/architecture/frontend-structure.md` - Frontend layers, atomic design, store pattern
- `CONTRIBUTING.md` - Setup, conventions, testing, migrations
- `backend/orders/notifications/README.md` - Service architecture example
- `backend/schema.yml` - OpenAPI spec (generated by drf-spectacular)

**Migration History**: The project is actively migrating from Django templates to Vue 3 SPA. Orders feature is fully migrated and serves as the reference implementation. Other features (members, inventory) are partially migrated.

## When Making Changes

1. **New API endpoint**: Add to `{app}/api/viewsets/`, register in `rest_urls.py`
2. **New component**: Follow atomic design, put in correct level (atoms/molecules/organisms)
3. **New store**: Use Composition API pattern, include loading/error states
4. **Schema changes**: Always create Django migrations
5. **Status changes**: Use `OrderWorkflowService` for validation

---


General Instructiosn: 
----
  - avoid generading markdown files if not explicitly asked and only if you need them to store some strategies or plans for yourself. 
  - when generating code, ensure it is syntactically correct and follows best practices for the given programming language.
  - When referencing existing code or documentation, ensure that your suggestions align with the established patterns and conventions used in the project.
  - When suggesting changes to the codebase, ensure that they are consistent with the project's architecture and coding standards.
  - For new features or significant changes, provide clear instructions on where and how to implement them within the existing code structure.
  - create Tests where applicable to ensure code quality and reliability. (e2e, unit, integration)
  - ensure that generated API endpoints follow RESTful principles and integrate seamlessly with the existing backend structure. Use Django REST Framework best practices. All Endpoints must be added to the appropriate ViewSets in the `api/viewsets/` directory of the relevant Django app. They need to be authenticated using JWT and must return data in the established paginated format where applicable. Permissions should be enforced using the existing permission classes defined in `permissions.py`.
  - Test the permissions and authentication of new API endpoints to ensure they align with the project's security requirements.
  - **MANDATORY before completing any code changes — run all checks locally and fix every error:**
    - Frontend TypeScript: `cd frontend && npm run type-check`
    - Frontend lint: `cd frontend && npm run lint`
    - Backend lint/format: `cd backend && pipenv run ruff check . && pipenv run ruff format --check .`
    - If any check fails, fix all issues before finishing. Never skip this step.

**Reference Implementation**: `backend/orders/api/` + `frontend/src/components/orders/`
