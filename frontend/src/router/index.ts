import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: () => import('@/components/layout/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue')
        },
        // Members
        {
          path: 'members',
          name: 'members',
          component: () => import('@/views/MembersView.vue')
        },
        {
          path: 'members/create',
          name: 'members-create',
          component: () => import('@/views/MemberEditView.vue')
        },
        {
          path: 'members/:id',
          name: 'member-detail',
          component: () => import('@/views/MemberDetailView.vue')
        },
        {
          path: 'members/:id/edit',
          name: 'member-edit',
          component: () => import('@/views/MemberEditView.vue')
        },
        // Parents
        {
          path: 'parents',
          name: 'parents',
          component: () => import('@/views/ParentsView.vue')
        },
        {
          path: 'parents/create',
          name: 'parents-create',
          component: () => import('@/views/ParentEditView.vue')
        },
        {
          path: 'parents/:id/edit',
          name: 'parent-edit',
          component: () => import('@/views/ParentEditView.vue')
        },
        // Servicebook
        {
          path: 'servicebook',
          name: 'servicebook',
          component: () => import('@/views/ServicebookView.vue')
        },
        // Other modules
        {
          path: 'inventory',
          name: 'inventory',
          component: () => import('@/views/InventoryView.vue')
        },
        {
          path: 'orders',
          name: 'orders',
          component: () => import('@/views/OrdersView.vue')
        },
        {
          path: 'qualifications',
          name: 'qualifications',
          component: () => import('@/views/QualificationsView.vue')
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue')
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/ProfileView.vue')
        }
      ]
    }
  ]
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
