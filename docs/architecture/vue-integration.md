# Vue.js + Pinia Integration Guide

Patterns for integrating the JF-Manager REST API with the Vue 3 + Pinia frontend.

## Project Structure

```mermaid
flowchart TD
  root[frontend/src]

  root --> api[api]
  api --> apiIndex[index.ts<br/>Axios instance with JWT auth]
  api --> apiAuth[auth.ts<br/>Auth endpoints]
  api --> apiMembers[members.ts<br/>Members endpoints]
  api --> apiInventory[inventory.ts<br/>Inventory endpoints]
  api --> apiOrders[orders.ts<br/>Orders endpoints]

  root --> stores[stores]
  stores --> storeAuth[auth.ts<br/>Authentication store]
  stores --> storeMembers[members.ts<br/>Members store]
  stores --> storeInventory[inventory.ts<br/>Inventory store]
  stores --> storeOrders[orders.ts<br/>Orders store]

  root --> types[types]
  types --> typesOrders[orders.ts<br/>TypeScript interfaces]

  root --> components[components]
  components --> orders[orders]
  orders --> atoms[atoms<br/>Single-purpose components]
  orders --> molecules[molecules<br/>Composed features]
  orders --> organisms[organisms<br/>Complex state-aware components]

  root --> router[router]
```

## API Client

The base API client (`api/index.ts`) uses the browser session cookie set by the backend. The SPA never sees an access token:

```typescript
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  withCredentials: true,           // HttpOnly session cookie
  xsrfCookieName: 'csrftoken',     // Django CSRF cookie …
  xsrfHeaderName: 'X-CSRFToken',   // … returned as header on writes
})
```

- SPA and API must share one origin (production: Nginx proxies `/api`; development: Vite proxies `/api`, `/admin`, `/static` to `VITE_BACKEND_URL`).
- A `401` outside `/auth/session/*` reports an expired session to the auth store, which clears all state and reloads `/login`.
- A `403` with `code: "mfa_setup_required"` sends the user to the MFA setup in the profile.
- Login: `POST /auth/session/login/`, optionally followed by `POST /auth/session/mfa/`; status via `GET /auth/session/`; logout via `POST /auth/session/logout/`.

## API Endpoint Pattern

```typescript
import apiClient from './index'
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
  },
}
```

## Pinia Store Pattern (Composition API)

All stores use `defineStore(() => {})` (Composition API):

```typescript
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { ordersApi } from '@/api/orders'
import type { Order } from '@/types/orders'

export const useOrdersStore = defineStore('orders', () => {
  const orders = ref<Order[]>([])
  const loading = ref(false)

  const hasOrders = computed(() => orders.value.length > 0)

  async function fetchOrders(params?: OrderListParams) {
    loading.value = true
    try {
      const response = await ordersApi.list(params)
      orders.value = response.data.results  // ← Extract .results!
      return orders.value
    } finally {
      loading.value = false
    }
  }

  return { orders, loading, hasOrders, fetchOrders }
})
```

**Key rules:**
- Components are **presentation-only** – all business logic in stores
- **Never** mutate store state from components – call store actions
- Always extract `.results` from paginated responses

## Component Patterns

### Props/Emits

```vue
<script setup lang="ts">
interface Props {
  orderId?: number
  initialData?: Order
}
const props = defineProps<Props>()

const emit = defineEmits<{
  success: [orderId: number]
  error: [error: unknown]
}>()
</script>
```

### Using Store Data

```vue
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useOrdersStore } from '@/stores/orders'

const ordersStore = useOrdersStore()
const orders = computed(() => ordersStore.orders)

onMounted(() => ordersStore.fetchOrders())
</script>
```

## Pagination Type

```typescript
interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
```

## Router Guards

```typescript
router.beforeEach((to) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'login' }
  }
})
```

## Reference Implementation

See `backend/orders/api/` + `frontend/src/components/orders/` for the complete pattern.
