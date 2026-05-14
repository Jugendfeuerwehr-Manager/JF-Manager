import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'

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
      path: '/auth/oidc/callback',
      name: 'oidc-callback',
      component: () => import('@/views/OIDCCallbackView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/forgot-password',
      name: 'forgot-password',
      component: () => import('@/views/PasswordResetRequestView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/reset-password/:uid/:token',
      name: 'reset-password',
      component: () => import('@/views/PasswordResetConfirmView.vue'),
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
          component: () => import('@/views/MembersView.vue'),
          meta: { requiresPerm: 'view_member' }
        },
        {
          path: 'groups',
          name: 'group-management',
          component: () => import('@/views/GroupManagementView.vue'),
          meta: { requiresPerm: 'view_group' }
        },
        // Lists
        {
          path: 'lists',
          name: 'lists',
          component: () => import('@/views/ListsView.vue'),
          meta: { requiresPerm: 'view_memberlist' }
        },
        {
          path: 'lists/:id',
          name: 'list-detail',
          component: () => import('@/views/ListDetailView.vue'),
          meta: { requiresPerm: 'view_memberlist' }
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
        // Emails
        {
          path: 'emails/compose',
          name: 'emails-compose',
          component: () => import('@/views/EmailComposeView.vue')
        },
        {
          path: 'emails/history',
          name: 'emails-history',
          component: () => import('@/views/EmailHistoryView.vue')
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
        // Inventory - Stock Management & Loans
        {
          path: 'inventory',
          name: 'inventory',
          component: () => import('@/components/inventory/InventoryView.vue')
        },
        {
          path: 'inventory/loans',
          name: 'inventory-loans',
          component: () => import('@/components/inventory/InventoryView.vue'),
          props: { initialTab: 'loans' }
        },
        {
          path: 'inventory/stock',
          name: 'inventory-stock',
          component: () => import('@/components/inventory/InventoryView.vue'),
          props: { initialTab: 'stock' }
        },
        {
          path: 'inventory/items',
          name: 'inventory-items',
          component: () => import('@/components/inventory/InventoryView.vue'),
          props: { initialTab: 'items' }
        },
        {
          path: 'inventory/locations',
          name: 'inventory-locations',
          component: () => import('@/components/inventory/InventoryView.vue'),
          props: { initialTab: 'locations' }
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
          component: () => import('@/views/SettingsView.vue'),
          meta: { requiresStaff: true },
          children: [
            {
              path: '',
              name: 'settings-index',
              component: () =>
                import('@/components/settings/organisms/SettingsOverview.vue'),
            },
            {
              path: 'general',
              name: 'settings-general',
              component: () =>
                import('@/components/settings/organisms/sections/GeneralSection.vue'),
            },
            {
              path: 'email',
              name: 'settings-email',
              component: () =>
                import('@/components/settings/organisms/sections/EmailSection.vue'),
            },
            {
              path: 'email-templates',
              name: 'settings-email-templates',
              component: () =>
                import('@/components/settings/organisms/sections/EmailTemplatesSection.vue'),
            },
            {
              path: 'member',
              name: 'settings-member',
              component: () =>
                import('@/components/settings/organisms/sections/MemberSection.vue'),
            },
            {
              path: 'service',
              name: 'settings-service',
              component: () =>
                import('@/components/settings/organisms/sections/ServiceSection.vue'),
            },
            {
              path: 'order',
              name: 'settings-order',
              component: () =>
                import('@/components/settings/organisms/sections/OrderSection.vue'),
            },
            {
              path: 'ldap',
              name: 'settings-ldap',
              component: () =>
                import('@/components/settings/organisms/sections/LdapSection.vue'),
            },
            {
              path: 'oidc',
              name: 'settings-oidc',
              component: () =>
                import('@/components/settings/organisms/sections/OidcSection.vue'),
            },
          ],
        },
        {
          path: 'users',
          name: 'admin-users',
          component: () => import('@/components/admin/organisms/UserManagementView.vue'),
          meta: { requiresStaff: true }
        },
        {
          path: 'departments',
          redirect: '/users'
        },
        {
          path: 'log',
          name: 'log',
          component: () => import('@/views/LogView.vue'),
          meta: { requiresStaff: true }
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('@/views/ProfileView.vue')
        },
        // Training / Ausbildungsplanung
        {
          path: 'training',
          name: 'training',
          component: () => import('@/views/training/TrainingCalendarView.vue')
        },
        {
          path: 'training/library',
          name: 'training-library',
          component: () => import('@/views/training/LibraryView.vue')
        },
        {
          path: 'training/sessions/:id/plan',
          name: 'training-planner',
          component: () => import('@/views/training/TrainingPlannerView.vue'),
          props: (route) => ({ sessionId: Number(route.params.id) })
        },
        {
          path: 'training/sessions/:id/handout',
          name: 'training-handout',
          component: () => import('@/views/training/TrainingHandoutView.vue'),
          props: (route) => ({ sessionId: Number(route.params.id) })
        }
      ]
    },
    // Mobile training planner — full-screen, no shell chrome
    {
      path: '/training/sessions/:id/mobile',
      name: 'training-mobile',
      component: () => import('@/views/training/TrainingMobilePlannerView.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const settingsStore = useSettingsStore()
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else if (to.meta.requiresStaff && authStore.isAuthenticated && !authStore.isOrgWide) {
    // Non-staff user trying to access a staff-only route → redirect to dashboard
    next('/')
  } else if (to.meta.requiresPerm && authStore.isAuthenticated && !authStore.hasPerm(to.meta.requiresPerm)) {
    // Missing permission for this route → redirect to dashboard
    next('/')
  } else {
    // Load settings if authenticated and not already loaded
    if (authStore.isAuthenticated && !settingsStore.general) {
      try {
        await settingsStore.fetchPermissions()
        if (settingsStore.canViewCategory('general')) {
          await settingsStore.fetchCategorySettings('general')
        }
      } catch (error) {
        // Silently fail - settings are optional
        console.warn('Failed to load general settings:', error)
      }
    }
    next()
  }
})

export default router
