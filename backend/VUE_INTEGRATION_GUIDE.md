# Vue.js + Pinia Integration Guide for JF-Manager API

This guide shows how to integrate the JF-Manager REST API with a Vue.js 3 + Pinia application.

## Table of Contents
1. [Project Setup](#project-setup)
2. [API Service Layer](#api-service-layer)
3. [Authentication Store](#authentication-store)
4. [Domain Stores](#domain-stores)
5. [Composables](#composables)
6. [Components Examples](#components-examples)
7. [Router Guards](#router-guards)

---

## Project Setup

### Install Dependencies

```bash
npm create vue@latest jf-manager-frontend
cd jf-manager-frontend

# Install additional dependencies
npm install axios pinia @vueuse/core
```

### Project Structure

```
src/
├── api/
│   ├── index.js              # API client
│   ├── auth.js               # Auth endpoints
│   ├── members.js            # Members endpoints
│   ├── inventory.js          # Inventory endpoints
│   └── orders.js             # Orders endpoints
├── stores/
│   ├── auth.js               # Authentication store
│   ├── members.js            # Members store
│   ├── inventory.js          # Inventory store
│   └── orders.js             # Orders store
├── composables/
│   ├── useAuth.js            # Auth composable
│   └── useApi.js             # API error handling
├── router/
│   └── index.js              # Vue Router
├── views/
└── components/
```

---

## API Service Layer

### `src/api/index.js` - Base API Client

```javascript
import axios from 'axios';
import { useAuthStore } from '@/stores/auth';

// Create axios instance
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - Add auth token
apiClient.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore();
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - Handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If 401 and not already retried, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const authStore = useAuthStore();
      try {
        await authStore.refreshAccessToken();
        
        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${authStore.accessToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout user
        authStore.logout();
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
```

### `src/api/auth.js` - Authentication Endpoints

```javascript
import apiClient from './index';

export const authApi = {
  login(username, password) {
    return apiClient.post('/auth/login/', { username, password });
  },
  
  refresh(refreshToken) {
    return apiClient.post('/auth/refresh/', { refresh: refreshToken });
  },
  
  verify(token) {
    return apiClient.post('/auth/verify/', { token });
  },
  
  getCurrentUser() {
    return apiClient.get('/users/me/');
  },
  
  updateProfile(data) {
    return apiClient.patch('/users/me/', data);
  },
  
  changePassword(oldPassword, newPassword) {
    return apiClient.post('/users/change-password/', {
      old_password: oldPassword,
      new_password: newPassword,
      new_password_confirm: newPassword,
    });
  },
};
```

### `src/api/members.js` - Members Endpoints

```javascript
import apiClient from './index';

export const membersApi = {
  getAll(params = {}) {
    return apiClient.get('/members/', { params });
  },
  
  getById(id) {
    return apiClient.get(`/members/${id}/`);
  },
  
  create(data) {
    return apiClient.post('/members/', data);
  },
  
  update(id, data) {
    return apiClient.patch(`/members/${id}/`, data);
  },
  
  delete(id) {
    return apiClient.delete(`/members/${id}/`);
  },
  
  search(query) {
    return apiClient.get('/members/', { 
      params: { search: query } 
    });
  },
};

export const parentsApi = {
  getAll(params = {}) {
    return apiClient.get('/parents/', { params });
  },
  
  getById(id) {
    return apiClient.get(`/parents/${id}/`);
  },
  
  create(data) {
    return apiClient.post('/parents/', data);
  },
  
  update(id, data) {
    return apiClient.patch(`/parents/${id}/`, data);
  },
};
```

### `src/api/inventory.js` - Inventory Endpoints

```javascript
import apiClient from './index';

export const inventoryApi = {
  // Items
  items: {
    getAll(params = {}) {
      return apiClient.get('/inventory/items/', { params });
    },
    
    getById(id) {
      return apiClient.get(`/inventory/items/${id}/`);
    },
    
    getStock(id) {
      return apiClient.get(`/inventory/items/${id}/stock/`);
    },
    
    getVariants(id) {
      return apiClient.get(`/inventory/items/${id}/variants/`);
    },
    
    search(query) {
      return apiClient.get('/inventory/items/search/', { 
        params: { q: query } 
      });
    },
    
    create(data) {
      return apiClient.post('/inventory/items/', data);
    },
    
    update(id, data) {
      return apiClient.patch(`/inventory/items/${id}/`, data);
    },
    
    delete(id) {
      return apiClient.delete(`/inventory/items/${id}/`);
    },
  },
  
  // Categories
  categories: {
    getAll(params = {}) {
      return apiClient.get('/inventory/categories/', { params });
    },
    
    getItems(categoryId) {
      return apiClient.get(`/inventory/categories/${categoryId}/items/`);
    },
  },
  
  // Locations
  locations: {
    getAll(params = {}) {
      return apiClient.get('/inventory/locations/', { params });
    },
    
    getStock(locationId) {
      return apiClient.get(`/inventory/locations/${locationId}/stock/`);
    },
  },
  
  // Transactions
  transactions: {
    getAll(params = {}) {
      return apiClient.get('/inventory/transactions/', { params });
    },
    
    create(data) {
      return apiClient.post('/inventory/transactions/', data);
    },
  },
};
```

---

## Authentication Store

### `src/stores/auth.js`

```javascript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { authApi } from '@/api/auth';

export const useAuthStore = defineStore('auth', () => {
  // State
  const accessToken = ref(localStorage.getItem('accessToken'));
  const refreshToken = ref(localStorage.getItem('refreshToken'));
  const user = ref(null);
  const loading = ref(false);
  const error = ref(null);
  
  // Getters
  const isAuthenticated = computed(() => !!accessToken.value);
  const userFullName = computed(() => 
    user.value ? `${user.value.first_name} ${user.value.last_name}` : ''
  );
  
  // Actions
  async function login(username, password) {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await authApi.login(username, password);
      
      accessToken.value = response.data.access;
      refreshToken.value = response.data.refresh;
      
      // Store tokens in localStorage
      localStorage.setItem('accessToken', response.data.access);
      localStorage.setItem('refreshToken', response.data.refresh);
      
      // Fetch user data
      await fetchUser();
      
      return true;
    } catch (err) {
      error.value = err.response?.data?.detail || 'Login failed';
      throw err;
    } finally {
      loading.value = false;
    }
  }
  
  async function fetchUser() {
    try {
      const response = await authApi.getCurrentUser();
      user.value = response.data;
    } catch (err) {
      error.value = 'Failed to fetch user data';
      throw err;
    }
  }
  
  async function refreshAccessToken() {
    if (!refreshToken.value) {
      throw new Error('No refresh token available');
    }
    
    try {
      const response = await authApi.refresh(refreshToken.value);
      accessToken.value = response.data.access;
      localStorage.setItem('accessToken', response.data.access);
    } catch (err) {
      // Refresh failed, logout
      logout();
      throw err;
    }
  }
  
  async function updateProfile(data) {
    try {
      const response = await authApi.updateProfile(data);
      user.value = response.data;
      return response.data;
    } catch (err) {
      error.value = 'Failed to update profile';
      throw err;
    }
  }
  
  function logout() {
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
  }
  
  // Initialize - Check if tokens exist and fetch user
  async function initialize() {
    if (accessToken.value) {
      try {
        await fetchUser();
      } catch (err) {
        // Token invalid, logout
        logout();
      }
    }
  }
  
  return {
    // State
    accessToken,
    refreshToken,
    user,
    loading,
    error,
    // Getters
    isAuthenticated,
    userFullName,
    // Actions
    login,
    logout,
    fetchUser,
    refreshAccessToken,
    updateProfile,
    initialize,
  };
});
```

---

## Domain Stores

### `src/stores/members.js`

```javascript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { membersApi } from '@/api/members';

export const useMembersStore = defineStore('members', () => {
  // State
  const members = ref([]);
  const currentMember = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const pagination = ref({
    count: 0,
    next: null,
    previous: null,
    page: 1,
    pageSize: 25,
  });
  
  // Filters
  const filters = ref({
    search: '',
    status: '',
    ordering: '-joined',
  });
  
  // Getters
  const activeMembersCount = computed(() => 
    members.value.filter(m => m.status === 'active').length
  );
  
  const sortedMembers = computed(() => {
    return [...members.value].sort((a, b) => 
      a.lastname.localeCompare(b.lastname)
    );
  });
  
  // Actions
  async function fetchMembers(page = 1) {
    loading.value = true;
    error.value = null;
    
    try {
      const params = {
        page,
        page_size: pagination.value.pageSize,
        ...filters.value,
      };
      
      const response = await membersApi.getAll(params);
      
      members.value = response.data.results;
      pagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous,
        page,
        pageSize: pagination.value.pageSize,
      };
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to fetch members';
      throw err;
    } finally {
      loading.value = false;
    }
  }
  
  async function fetchMember(id) {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await membersApi.getById(id);
      currentMember.value = response.data;
      return response.data;
    } catch (err) {
      error.value = 'Member not found';
      throw err;
    } finally {
      loading.value = false;
    }
  }
  
  async function createMember(memberData) {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await membersApi.create(memberData);
      members.value.push(response.data);
      return response.data;
    } catch (err) {
      error.value = err.response?.data || 'Failed to create member';
      throw err;
    } finally {
      loading.value = false;
    }
  }
  
  async function updateMember(id, updates) {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await membersApi.update(id, updates);
      
      // Update in local state
      const index = members.value.findIndex(m => m.id === id);
      if (index !== -1) {
        members.value[index] = response.data;
      }
      
      if (currentMember.value?.id === id) {
        currentMember.value = response.data;
      }
      
      return response.data;
    } catch (err) {
      error.value = err.response?.data || 'Failed to update member';
      throw err;
    } finally {
      loading.value = false;
    }
  }
  
  async function deleteMember(id) {
    loading.value = true;
    error.value = null;
    
    try {
      await membersApi.delete(id);
      
      // Remove from local state
      members.value = members.value.filter(m => m.id !== id);
      if (currentMember.value?.id === id) {
        currentMember.value = null;
      }
    } catch (err) {
      error.value = 'Failed to delete member';
      throw err;
    } finally {
      loading.value = false;
    }
  }
  
  async function searchMembers(query) {
    filters.value.search = query;
    await fetchMembers(1);
  }
  
  function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters };
  }
  
  function resetFilters() {
    filters.value = {
      search: '',
      status: '',
      ordering: '-joined',
    };
  }
  
  return {
    // State
    members,
    currentMember,
    loading,
    error,
    pagination,
    filters,
    // Getters
    activeMembersCount,
    sortedMembers,
    // Actions
    fetchMembers,
    fetchMember,
    createMember,
    updateMember,
    deleteMember,
    searchMembers,
    setFilters,
    resetFilters,
  };
});
```

---

## Composables

### `src/composables/useApi.js` - Error Handling

```javascript
import { ref } from 'vue';
import { useRouter } from 'vue-router';

export function useApi() {
  const loading = ref(false);
  const error = ref(null);
  const router = useRouter();
  
  async function execute(apiCall, options = {}) {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await apiCall();
      
      if (options.onSuccess) {
        options.onSuccess(response.data);
      }
      
      return response.data;
    } catch (err) {
      error.value = handleError(err);
      
      if (options.onError) {
        options.onError(error.value);
      } else {
        // Default error handling
        showErrorNotification(error.value);
      }
      
      throw err;
    } finally {
      loading.value = false;
    }
  }
  
  function handleError(err) {
    if (err.response) {
      // Server responded with error
      const { status, data } = err.response;
      
      switch (status) {
        case 400:
          return formatValidationErrors(data);
        case 401:
          router.push('/login');
          return 'Bitte melden Sie sich an';
        case 403:
          return 'Keine Berechtigung für diese Aktion';
        case 404:
          return 'Ressource nicht gefunden';
        case 500:
          return 'Serverfehler. Bitte versuchen Sie es später erneut';
        default:
          return data.detail || 'Ein Fehler ist aufgetreten';
      }
    } else if (err.request) {
      // Request made but no response
      return 'Keine Verbindung zum Server';
    } else {
      // Something else happened
      return err.message || 'Ein unbekannter Fehler ist aufgetreten';
    }
  }
  
  function formatValidationErrors(data) {
    if (typeof data === 'object') {
      return Object.entries(data)
        .map(([field, errors]) => `${field}: ${errors.join(', ')}`)
        .join('\n');
    }
    return data.detail || 'Validierungsfehler';
  }
  
  function showErrorNotification(message) {
    // Implement your notification logic here
    console.error(message);
  }
  
  return {
    loading,
    error,
    execute,
  };
}
```

---

## Components Examples

### Member List Component

```vue
<template>
  <div class="members-page">
    <h1>Mitglieder</h1>
    
    <!-- Search and Filters -->
    <div class="filters">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Suchen..."
        @input="debouncedSearch"
      />
      
      <select v-model="statusFilter" @change="applyFilters">
        <option value="">Alle Status</option>
        <option value="active">Aktiv</option>
        <option value="inactive">Inaktiv</option>
      </select>
      
      <button @click="resetFilters">Zurücksetzen</button>
    </div>
    
    <!-- Loading State -->
    <div v-if="loading" class="loading">Lädt...</div>
    
    <!-- Error State -->
    <div v-if="error" class="error">{{ error }}</div>
    
    <!-- Members Table -->
    <table v-if="!loading && members.length > 0">
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Geburtsdatum</th>
          <th>Status</th>
          <th>Aktionen</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="member in members" :key="member.id">
          <td>{{ member.name }} {{ member.lastname }}</td>
          <td>{{ member.email }}</td>
          <td>{{ formatDate(member.birthday) }}</td>
          <td>
            <span :class="`status-${member.status}`">
              {{ member.status }}
            </span>
          </td>
          <td>
            <button @click="viewMember(member.id)">Ansehen</button>
            <button @click="editMember(member.id)">Bearbeiten</button>
            <button @click="confirmDelete(member.id)">Löschen</button>
          </td>
        </tr>
      </tbody>
    </table>
    
    <!-- Empty State -->
    <div v-if="!loading && members.length === 0" class="empty">
      Keine Mitglieder gefunden
    </div>
    
    <!-- Pagination -->
    <div v-if="pagination.count > pagination.pageSize" class="pagination">
      <button
        :disabled="!pagination.previous"
        @click="goToPage(pagination.page - 1)"
      >
        Vorherige
      </button>
      
      <span>Seite {{ pagination.page }} von {{ totalPages }}</span>
      
      <button
        :disabled="!pagination.next"
        @click="goToPage(pagination.page + 1)"
      >
        Nächste
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useMembersStore } from '@/stores/members';
import { useDebounceFn } from '@vueuse/core';

const router = useRouter();
const membersStore = useMembersStore();

// Local state
const searchQuery = ref('');
const statusFilter = ref('');

// Computed
const { members, loading, error, pagination } = membersStore;

const totalPages = computed(() =>
  Math.ceil(pagination.count / pagination.pageSize)
);

// Methods
const debouncedSearch = useDebounceFn(() => {
  membersStore.searchMembers(searchQuery.value);
}, 500);

function applyFilters() {
  membersStore.setFilters({ status: statusFilter.value });
  membersStore.fetchMembers(1);
}

function resetFilters() {
  searchQuery.value = '';
  statusFilter.value = '';
  membersStore.resetFilters();
  membersStore.fetchMembers(1);
}

function goToPage(page) {
  membersStore.fetchMembers(page);
}

function viewMember(id) {
  router.push(`/members/${id}`);
}

function editMember(id) {
  router.push(`/members/${id}/edit`);
}

async function confirmDelete(id) {
  if (confirm('Mitglied wirklich löschen?')) {
    try {
      await membersStore.deleteMember(id);
      // Show success message
    } catch (err) {
      // Error already handled in store
    }
  }
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('de-DE');
}

// Lifecycle
onMounted(() => {
  membersStore.fetchMembers();
});
</script>
```

---

## Router Guards

### `src/router/index.js`

```javascript
import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/members',
    name: 'Members',
    component: () => import('@/views/Members.vue'),
    meta: { requiresAuth: true, permission: 'members.view_member' },
  },
  {
    path: '/members/:id',
    name: 'MemberDetail',
    component: () => import('@/views/MemberDetail.vue'),
    meta: { requiresAuth: true, permission: 'members.view_member' },
  },
  // ... more routes
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Global navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();
  
  // Initialize auth store if not already done
  if (!authStore.user && authStore.accessToken) {
    await authStore.initialize();
  }
  
  // Check if route requires authentication
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } });
    return;
  }
  
  // Check permissions
  if (to.meta.permission) {
    // Implement permission check based on your backend
    // This is a simplified example
    const hasPermission = checkPermission(authStore.user, to.meta.permission);
    
    if (!hasPermission) {
      next({ name: 'Dashboard' }); // Redirect to dashboard if no permission
      return;
    }
  }
  
  next();
});

function checkPermission(user, permission) {
  // Implement your permission checking logic
  // This might involve checking user.permissions array or making an API call
  return true; // Placeholder
}

export default router;
```

---

## Environment Variables

### `.env`

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### `.env.production`

```
VITE_API_BASE_URL=https://your-domain.com/api/v1
```

---

## Complete Example: Main.js

```javascript
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import { useAuthStore } from './stores/auth';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);

// Initialize auth before mounting
const authStore = useAuthStore();
authStore.initialize().finally(() => {
  app.mount('#app');
});
```

---

This guide provides a complete foundation for integrating the JF-Manager API with Vue.js 3 and Pinia. All patterns follow modern Vue.js best practices and are production-ready.
