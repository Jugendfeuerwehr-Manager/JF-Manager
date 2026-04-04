<template>
  <div class="layout-wrapper">
    <!-- Desktop: Top Navigation Bar -->
    <AppTopbar v-if="!isMobile" @menu-click="toggleNavigation" />

    <!-- Mobile: PrimeVue Toolbar -->
    <Toolbar v-else class="mobile-toolbar">
      <template #start>
        <Button
          icon="pi pi-bars"
          text
          rounded
          class="mobile-toolbar-button"
          @click="toggleNavigation"
          aria-label="Navigation öffnen"
        />
        <div class="mobile-toolbar-title">
          <i class="pi pi-shield"></i>
          <span>{{ websiteTitle }}</span>
        </div>
      </template>
      <template #end>
        <div class="mobile-toolbar-end">
          <Button
            :icon="themeIcon"
            text
            rounded
            size="small"
            class="mobile-toolbar-button"
            aria-label="Theme wechseln"
            @click="cycleTheme"
          />
          <Avatar
            :label="userInitials"
            shape="circle"
            size="normal"
            class="mobile-toolbar-avatar"
            @click="toggleUserMenu"
          />
        </div>
      </template>
    </Toolbar>

    <!-- Main Content -->
    <div class="layout-main" :class="{ 'has-bottom-nav': isMobile }">
      <div class="layout-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </div>

    <!-- Mobile: Bottom Tab Navigation -->
    <div v-if="isMobile" class="mobile-bottom-nav">
      <TabMenu
        :model="mobileNavItems"
        :active-index="mobileActiveIndex"
        class="mobile-tabmenu"
      />
    </div>

    <!-- PrimeVue Sidebar for global navigation -->
    <Sidebar
      v-model:visible="navigationVisible"
      position="left"
      class="menu-sidebar"
      @hide="navigationVisible = false"
    >
      <template #header>
        <div class="sidebar-header">
          <i class="pi pi-shield"></i>
          <span>{{ websiteTitle }}</span>
        </div>
      </template>

      <div class="sidebar-nav">
        <div
          v-for="section in sidebarSections"
          :key="section.label"
          class="sidebar-section"
        >
          <p class="sidebar-section__label">{{ section.label }}</p>
          <div class="sidebar-links">
            <button
              v-for="item in section.items"
              :key="item.to ?? item.label ?? item.icon"
              class="sidebar-link"
              :class="{ 'is-active': isActivePath(item) }"
              type="button"
              @click="navigateTo(item)"
            >
              <i :class="item.icon"></i>
              <span>{{ item.label }}</span>
            </button>
          </div>
        </div>
      </div>

      <Divider />

      <Button
        label="Abmelden"
        icon="pi pi-sign-out"
        severity="danger"
        outlined
        class="w-full"
        @click="handleLogout"
      />
    </Sidebar>

    <!-- User Menu -->
    <Menu ref="userMenu" :model="userMenuItems" popup />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppSettings } from '@/composables/useAppSettings'
import { useTheme } from '@/composables/useTheme'
import AppTopbar from './AppTopbar.vue'
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import Sidebar from 'primevue/sidebar'
import Divider from 'primevue/divider'
import Menu from 'primevue/menu'
import Toolbar from 'primevue/toolbar'
import TabMenu from 'primevue/tabmenu'
import type { MenuItem } from 'primevue/menuitem'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { websiteTitle } = useAppSettings()
const { themeMode, setMode } = useTheme()
const userMenu = ref()

const isMobile = ref(window.innerWidth < 768)
const navigationVisible = ref(false)

const createNavItem = (label: string, icon: string, to: string): MenuItem => ({
  label,
  icon,
  to,
  command: () => router.push(to)
})

const mainNavItems: MenuItem[] = [
  createNavItem('Mitglieder', 'pi pi-users', '/members'),
  createNavItem('Eltern', 'pi pi-user', '/parents'),
  createNavItem('Dienstbuch', 'pi pi-book', '/servicebook')
]

const secondaryNavItems: MenuItem[] = [
  createNavItem('Dashboard', 'pi pi-home', '/'),
  createNavItem('Protokoll', 'pi pi-list', '/log'),
  createNavItem('Inventar', 'pi pi-box', '/inventory'),
  createNavItem('Bestellungen', 'pi pi-shopping-cart', '/orders'),
  createNavItem('E-Mails', 'pi pi-envelope', '/emails/compose'),
  createNavItem('Qualifikationen', 'pi pi-crown', '/qualifications'),
  createNavItem('Einstellungen', 'pi pi-cog', '/settings')
]

const membersNavItem = mainNavItems.find(item => item.to === '/members')
const servicebookNavItem = mainNavItems.find(item => item.to === '/servicebook')
const ordersNavItem = secondaryNavItems.find(item => item.to === '/orders')

const sidebarSections = computed(() => [
  { label: 'Hauptmodule', items: mainNavItems },
  { label: 'Weitere Bereiche', items: secondaryNavItems }
])

const mobileNavItems = computed<MenuItem[]>(() => {
  return [membersNavItem, servicebookNavItem, ordersNavItem].filter(Boolean) as MenuItem[]
})

const mobileActiveIndex = computed(() => {
  const currentPath = route.path
  const index = mobileNavItems.value.findIndex(item => {
    if (!item.to) return false
    return currentPath.startsWith(item.to as string)
  })
  return index === -1 ? 0 : index
})

const userInitials = computed(() => {
  if (!authStore.user) return 'U'
  const first = authStore.user.first_name?.[0] || ''
  const last = authStore.user.last_name?.[0] || ''
  return `${first}${last}`.toUpperCase()
})

const userMenuItems: MenuItem[] = [
  {
    label: 'Profil',
    icon: 'pi pi-user',
    command: () => router.push('/profile')
  },
  {
    label: 'Einstellungen',
    icon: 'pi pi-cog',
    command: () => router.push('/settings')
  },
  {
    separator: true
  },
  {
    label: 'Abmelden',
    icon: 'pi pi-sign-out',
    command: () => authStore.logout()
  }
]

const toggleNavigation = () => {
  navigationVisible.value = !navigationVisible.value
}

const toggleUserMenu = (event: Event) => {
  userMenu.value.toggle(event)
}

const handleLogout = () => {
  navigationVisible.value = false
  authStore.logout()
}

const isActivePath = (item: MenuItem) => {
  if (!item.to) return false
  const target = item.to as string
  return route.path === target || route.path.startsWith(`${target}/`)
}

const navigateTo = (item: MenuItem) => {
  if (!item.to) return
  router.push(item.to as string)
  navigationVisible.value = false
}

const themeIcon = computed(() => {
  if (themeMode.value === 'dark') return 'pi pi-moon'
  if (themeMode.value === 'light') return 'pi pi-sun'
  return 'pi pi-desktop'
})

const cycleTheme = () => {
  const order: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system']
  const idx = order.indexOf(themeMode.value)
  setMode(order[(idx + 1) % order.length] as 'light' | 'dark' | 'system')
}

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
}

watch(
  () => route.path,
  () => {
    if (navigationVisible.value) {
      navigationVisible.value = false
    }
  }
)

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.layout-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--surface-ground);
}

/* Main Content */
.layout-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.layout-main.has-bottom-nav {
  padding-bottom: 80px; /* Space for bottom nav */
  margin-top: 60px; /* Space for mobile toolbar */
}

.layout-content {
  flex: 1;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
}

/* Desktop: Add top padding */
@media (min-width: 768px) {
  .layout-main {
    margin-top: 70px;
  }
  
  .layout-content {
    padding: 2rem;
  }
}

.mobile-toolbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  border-bottom: 1px solid var(--p-menu-border-color);
  background: var(--p-menu-background);
  height: 60px;
}

.mobile-toolbar-button {
  color: var(--text-color-secondary);
}

.mobile-toolbar-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--primary-color);
}

.mobile-toolbar-avatar {
  cursor: pointer;
}

.mobile-toolbar-end {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.mobile-bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  border-top: 1px solid var(--p-menu-border-color);
  background: var(--p-menu-background);
}

.mobile-tabmenu :deep(.p-tabmenu-nav) {
  justify-content: space-around;
}

.mobile-tabmenu :deep(.p-menuitem-link) {
  flex-direction: column;
  gap: 0.25rem;
}

.menu-sidebar {
  max-width: 22rem;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--primary-color);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.sidebar-section__label {
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-color-secondary);
  margin-bottom: 0.5rem;
}

.sidebar-links {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  width: 100%;
  padding: 0.6rem 0.75rem;
  border-radius: var(--border-radius);
  border: 1px solid var(--surface-border);
  background: transparent;
  color: var(--text-color);
  font-weight: 500;
  text-align: left;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.sidebar-link i {
  font-size: 1rem;
  color: currentColor;
}

.sidebar-link:hover {
  background: var(--surface-100);
}

.sidebar-link.is-active {
  background: var(--primary-100);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Hide mobile elements on desktop */
@media (min-width: 768px) {
  .mobile-toolbar,
  .mobile-bottom-nav {
    display: none;
  }
}
</style>
