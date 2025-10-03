<template>
  <div class="app-topbar">
    <div class="topbar-content">
      <div class="topbar-start">
        <div class="logo" @click="$router.push('/')">
          <i class="pi pi-shield"></i>
          <span class="logo-text">JF-Manager</span>
        </div>

        <!-- Desktop Navigation Menu -->
        <nav class="desktop-nav">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            active-class="active"
          >
            <i :class="item.icon"></i>
            <span>{{ item.label }}</span>
          </router-link>
          
          <button class="nav-item" @click="emit('menuClick')">
            <i class="pi pi-ellipsis-h"></i>
            <span>Mehr</span>
          </button>
        </nav>
      </div>

      <div class="topbar-end">
        <div class="user-profile" @click="toggleUserMenu">
          <Avatar
            :label="userInitials"
            shape="circle"
            class="user-avatar"
            size="normal"
          />
          <div class="user-info">
            <span class="user-name">{{ authStore.user?.first_name || 'User' }}</span>
          </div>
          <i class="pi pi-angle-down"></i>
        </div>
        <Menu ref="userMenu" :model="userMenuItems" popup class="user-menu" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Avatar from 'primevue/avatar'
import Menu from 'primevue/menu'

const emit = defineEmits<{
  menuClick: []
}>()

const router = useRouter()
const authStore = useAuthStore()
const userMenu = ref()

// Main navigation items for desktop top bar
const navItems = [
  { path: '/members', label: 'Mitglieder', icon: 'pi pi-users' },
  { path: '/parents', label: 'Eltern', icon: 'pi pi-user' },
  { path: '/servicebook', label: 'Dienstbuch', icon: 'pi pi-book' }
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

const toggleUserMenu = (event: Event) => {
  userMenu.value.toggle(event)
}
</script>

<style scoped>
.app-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  height: 70px;
  background: var(--p-menu-background);
  border-bottom: 1px solid var(--p-menu-border-color);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.topbar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 1.5rem;
  max-width: 1600px;
  margin: 0 auto;
}

.topbar-start {
  display: flex;
  align-items: center;
  gap: 2rem;
  flex: 1;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--primary-color);
  font-weight: 700;
  font-size: 1.5rem;
}

.logo i {
  font-size: 2rem;
}

.logo-text {
  display: inline;
}

/* Desktop Navigation */
.desktop-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: var(--border-radius);
  color: var(--text-color);
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s;
  cursor: pointer;
  border: none;
  background: none;
  font-size: 1rem;
}

.nav-item:hover {
  background: var(--surface-hover);
  color: var(--p-button-primary-background);
}

.nav-item.active {
  background: var(--p-button-primary-background);
  color: var(--p-button-primary-color);
}

.nav-item i {
  font-size: 1.1rem;
}

.topbar-end {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.topbar-end :deep(.p-button) {
  color: var(--text-color) !important;
}

.topbar-end :deep(.p-button:hover) {
  background: var(--surface-hover) !important;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: all 0.2s;
}

.user-profile:hover {
  background: var(--surface-hover);
}

.user-avatar {
  background: var(--primary-color);
  color: white;
  font-weight: 600;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  color: var(--text-color);
}

.user-name {
  font-weight: 600;
  font-size: 0.9rem;
  line-height: 1.2;
}

.user-role {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.user-profile i {
  color: var(--text-color-secondary);
  margin-left: 0.5rem;
}

:deep(.user-menu) {
  margin-top: 0.5rem;
}
</style>
