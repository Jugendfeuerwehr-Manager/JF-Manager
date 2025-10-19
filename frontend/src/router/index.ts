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
          component: () => import('@/views/ServicesListView.vue')
        },
        {
          path: 'servicebook/create',
          name: 'service-create',
          component: () => import('@/views/ServiceFormView.vue')
        },
        {
          path: 'servicebook/:id/edit',
          name: 'service-edit',
          component: () => import('@/views/ServiceFormView.vue')
        },
        // Other modules
        {
          path: 'inventory',
          name: 'inventory',
          component: () => import('@/views/InventoryView.vue')
        },
        // Orders
        {
          path: 'orders',
          name: 'orders',
          component: () => import('@/views/OrdersView.vue')
        },
        {
          path: 'orders/analytics',
          name: 'orders-analytics',
          component: () => import('@/components/orders/AnalyticsView.vue')
        },
        {
          path: 'orders/quick',
          name: 'orders-quick',
          component: () => import('@/views/QuickOrderView.vue')
        },
        {
          path: 'orders/create',
          name: 'orders-create',
          component: () => import('@/components/orders/OrderFormView.vue')
        },
        {
          path: 'orders/:id',
          name: 'order-detail',
          component: () => import('@/components/orders/OrderDetailView.vue'),
          props: (route) => ({ orderId: Number(route.params.id) })
        },
        {
          path: 'orders/:id/edit',
          name: 'order-edit',
          component: () => import('@/components/orders/OrderFormView.vue'),
          props: (route) => ({ orderId: Number(route.params.id) })
        },
        {
          path: 'qualifications',
          name: 'qualifications',
          component: () => import('@/views/qualifications/QualificationsDashboardView.vue')
        },
        {
          path: 'qualifications/types',
          name: 'qualification-types',
          component: () => import('@/views/qualifications/QualificationTypesManagementView.vue')
        },
        {
          path: 'qualifications/create',
          name: 'qualification-create',
          component: () => import('@/views/qualifications/QualificationCreateView.vue')
        },
        {
          path: 'qualifications/:id/edit',
          name: 'qualification-edit',
          component: () => import('@/views/qualifications/QualificationEditView.vue')
        },
        {
          path: 'qualifications/:id',
          name: 'qualification-detail',
          component: () => import('@/views/qualifications/QualificationDetailView.vue')
        },
        {
          path: 'qualifications/specialtasks/types',
          name: 'specialtask-types',
          component: () => import('@/views/qualifications/SpecialTaskTypesManagementView.vue')
        },
        {
          path: 'qualifications/specialtasks/create',
          name: 'specialtask-create',
          component: () => import('@/views/qualifications/SpecialTaskCreateView.vue')
        },
        {
          path: 'qualifications/specialtasks/:id/edit',
          name: 'specialtask-edit',
          component: () => import('@/views/qualifications/SpecialTaskEditView.vue')
        },
        {
          path: 'qualifications/specialtasks/:id',
          name: 'specialtask-detail',
          component: () => import('@/views/qualifications/SpecialTaskDetailView.vue')
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
