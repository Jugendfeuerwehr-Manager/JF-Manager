<template>
  <div class="layout-wrapper">
    <!-- Desktop: Top Navigation Bar -->
    <AppTopbar v-if="!isMobile" @menu-click="toggleMenu" />
    
    <!-- Mobile: Header (optional, minimal) -->
    <div v-else class="mobile-header">
      <div class="logo">
        <i class="pi pi-shield"></i>
        <span class="logo-text">JF-Manager</span>
      </div>
      <div class="mobile-header-actions">
        <Avatar
          :label="userInitials"
          shape="circle"
          size="normal"
          @click="toggleUserMenu"
        />
      </div>
    </div>

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
    <div v-if="isMobile" class="bottom-nav">
      <router-link
        v-for="item in mainNavItems"
        :key="item.path"
        :to="item.path"
        class="bottom-nav-item"
        active-class="active"
      >
        <i :class="item.icon"></i>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
      <button class="bottom-nav-item" @click="toggleMenu">
        <i class="pi pi-bars"></i>
        <span class="nav-label">Mehr</span>
      </button>
    </div>

    <!-- Menu Overlay (for "Mehr" button on mobile and desktop menu) -->
    <Sidebar
      v-model:visible="menuVisible"
      :position="isMobile ? 'bottom' : 'right'"
      class="menu-sidebar"
    >
      <template #header>
        <h3 class="m-0">{{ isMobile ? 'Menü' : 'Navigation' }}</h3>
      </template>
      
      <div class="menu-content">
        <div class="menu-section">
          <h4 class="menu-section-title">Hauptmodule</h4>
          <router-link
            v-for="item in mainNavItems"
            :key="item.path"
            :to="item.path"
            class="menu-item"
            @click="menuVisible = false"
          >
            <i :class="item.icon"></i>
            <span>{{ item.label }}</span>
          </router-link>
        </div>

        <Divider />

        <div class="menu-section">
          <h4 class="menu-section-title">Weitere Module</h4>
          <router-link
            v-for="item in secondaryNavItems"
            :key="item.path"
            :to="item.path"
            class="menu-item"
            @click="menuVisible = false"
          >
            <i :class="item.icon"></i>
            <span>{{ item.label }}</span>
          </router-link>
        </div>

        <Divider />

        <div class="menu-section">
          <button class="menu-item" @click="handleLogout">
            <i class="pi pi-sign-out"></i>
            <span>Abmelden</span>
          </button>
        </div>
      </div>
    </Sidebar>

    <!-- User Menu -->
    <Menu ref="userMenu" :model="userMenuItems" popup />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppTopbar from './AppTopbar.vue'
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import Sidebar from 'primevue/sidebar'
import Divider from 'primevue/divider'
import Menu from 'primevue/menu'

const router = useRouter()
const authStore = useAuthStore()
const userMenu = ref()

const isMobile = ref(window.innerWidth < 768)
const menuVisible = ref(false)

// Main navigation items (shown in bottom nav on mobile)
const mainNavItems = [
  { path: '/members', label: 'Mitglieder', icon: 'pi pi-users' },
  { path: '/parents', label: 'Eltern', icon: 'pi pi-user' },
  { path: '/servicebook', label: 'Dienstbuch', icon: 'pi pi-book' }
]

// Secondary navigation items (shown in menu)
const secondaryNavItems = [
  { path: '/', label: 'Dashboard', icon: 'pi pi-home' },
  { path: '/inventory', label: 'Inventar', icon: 'pi pi-box' },
  { path: '/orders', label: 'Bestellungen', icon: 'pi pi-shopping-cart' },
  { path: '/qualifications', label: 'Qualifikationen', icon: 'pi pi-certificate' },
  { path: '/settings', label: 'Einstellungen', icon: 'pi pi-cog' }
]

const userInitials = computed(() => {
  if (!authStore.user) return 'U'
  const first = authStore.user.first_name?.[0] || ''
  const last = authStore.user.last_name?.[0] || ''
  return `${first}${last}`.toUpperCase()
})

const userMenuItems = [
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

const toggleMenu = () => {
  menuVisible.value = !menuVisible.value
}

const toggleUserMenu = (event: Event) => {
  userMenu.value.toggle(event)
}

const handleLogout = () => {
  menuVisible.value = false
  authStore.logout()
}

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
}

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

/* Mobile Header */
.mobile-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: var(--p-menu-background);
  border-bottom: 2px solid var(--p-menu-border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
  z-index: 1000;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--primary-color);
}

.logo i {
  font-size: 1.5rem;
}

.mobile-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Main Content */
.layout-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.layout-main.has-bottom-nav {
  padding-bottom: 70px; /* Space for bottom nav */
  margin-top: 60px; /* Space for mobile header */
}

.layout-content {
  flex: 1;
  padding: 1.5rem;
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

/* Bottom Navigation (Mobile only) */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 70px;
  background: var(--p-menu-background);
  border-top: 1px solid var(--p-menu-border-color);
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 0.5rem 0;
  z-index: 1000;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
}

.bottom-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 0.25rem;
  color: var(--text-color-secondary);
  text-decoration: none;
  transition: all 0.2s;
  padding: 0.5rem;
  border: none;
  background: none;
  cursor: pointer;
}

.bottom-nav-item i {
  font-size: 1.5rem;
}

.nav-label {
  font-size: 0.75rem;
  font-weight: 500;
}

.bottom-nav-item:hover,
.bottom-nav-item:active {
  color: var(--primary-color);
}

.bottom-nav-item.active {
  color: var(--primary-color);
  font-weight: 600;
}

.bottom-nav-item.active i {
  transform: scale(1.1);
}

/* Menu Sidebar */
.menu-sidebar :deep(.p-sidebar) {
  width: 100%;
  max-width: 400px;
}

.menu-content {
  padding: 1rem 0;
}

.menu-section {
  padding: 0 0.5rem;
}

.menu-section-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-color-secondary);
  margin: 0.5rem 0;
  padding: 0 0.75rem;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  border-radius: var(--border-radius);
  color: var(--text-color);
  text-decoration: none;
  transition: all 0.2s;
  cursor: pointer;
  border: none;
  background: none;
  width: 100%;
  font-size: 1rem;
}

.menu-item:hover {
  background: var(--surface-hover);
  color: var(--primary-color);
}

.menu-item i {
  font-size: 1.25rem;
  width: 1.5rem;
  text-align: center;
}



.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Hide mobile elements on desktop */
@media (min-width: 768px) {
  .mobile-header,
  .bottom-nav {
    display: none;
  }
}
</style>
