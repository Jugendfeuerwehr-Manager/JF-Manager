<template>
  <div class="app-topbar">
    <Toolbar class="topbar-menubar">
      <template #start>
        <router-link class="logo" to="/">
          <span class="brand-mark" aria-hidden="true"><i class="pi pi-shield"></i></span>
          <span class="logo-text">{{ websiteTitle }}</span>
        </router-link>
      </template>

      <template #end>
        <div class="topbar-end">
          <!-- Department switcher -->
          <DepartmentSwitcher />
          <StaffNotificationBell />
          <!-- Dark/Light/System mode toggle -->
          <div class="theme-toggle" role="group" aria-label="Theme wählen">
            <Button
              v-tooltip.bottom="'Hell'"
              icon="pi pi-sun"
              text
              rounded
              size="small"
              :severity="themeMode === 'light' ? 'primary' : 'secondary'"
              :class="{ 'theme-btn-active': themeMode === 'light' }"
              aria-label="Helles Theme"
              @click="setMode('light')"
            />
            <Button
              v-tooltip.bottom="'Dunkel'"
              icon="pi pi-moon"
              text
              rounded
              size="small"
              :severity="themeMode === 'dark' ? 'primary' : 'secondary'"
              :class="{ 'theme-btn-active': themeMode === 'dark' }"
              aria-label="Dunkles Theme"
              @click="setMode('dark')"
            />
            <Button
              v-tooltip.bottom="'System'"
              icon="pi pi-desktop"
              text
              rounded
              size="small"
              :severity="themeMode === 'system' ? 'primary' : 'secondary'"
              :class="{ 'theme-btn-active': themeMode === 'system' }"
              aria-label="System Theme"
              @click="setMode('system')"
            />
          </div>

          <button type="button" class="user-profile" aria-label="Benutzermenü öffnen" aria-haspopup="menu" @click="toggleUserMenu">
            <Avatar
              :label="userInitials"
              shape="circle"
              class="user-avatar"
              size="normal"
            />
            <div class="user-info">
              <span class="user-name">{{ authStore.user?.first_name || 'Benutzer' }}</span>
            </div>
            <i class="pi pi-angle-down"></i>
          </button>
        </div>
      </template>
    </Toolbar>
    <Menu ref="userMenu" :model="userMenuItems" popup class="user-menu" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppSettings } from '@/composables/useAppSettings'
import { useTheme } from '@/composables/useTheme'
import Avatar from 'primevue/avatar'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import Toolbar from 'primevue/toolbar'
import type { MenuItem } from 'primevue/menuitem'
import StaffNotificationBell from '@/components/notifications/StaffNotificationBell.vue'
import DepartmentSwitcher from '@/components/departments/atoms/DepartmentSwitcher.vue'

const router = useRouter()
const authStore = useAuthStore()
const { websiteTitle } = useAppSettings()
const { themeMode, setMode } = useTheme()
const userMenu = ref()

const userInitials = computed(() => {
  if (!authStore.user) return 'U'
  const first = authStore.user.first_name?.[0] || ''
  const last = authStore.user.last_name?.[0] || ''
  return `${first}${last}`.toUpperCase()
})

const userMenuItems = computed<MenuItem[]>(() => [
  {
    label: 'Profil',
    icon: 'pi pi-user',
    command: () => router.push('/profile')
  },
  ...(authStore.isStaff ? [{
    label: 'Einstellungen',
    icon: 'pi pi-cog',
    command: () => router.push('/settings')
  }] : []),
  {
    separator: true
  },
  {
    label: 'Abmelden',
    icon: 'pi pi-sign-out',
    command: () => void authStore.logout()
  }
])

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
  height: 64px;
  background: var(--jf-color-card);
  border-bottom: 1px solid var(--jf-color-border);
}

.topbar-menubar {
  height: 100%;
  border: none;
  border-radius: 0;
  background: transparent;
  padding: 0 var(--jf-space-3);
  width: 100%;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  min-height: var(--jf-touch-target);
  border-radius: var(--jf-radius-md);
  text-decoration: none;
  color: var(--jf-color-text);
  font-weight: var(--jf-weight-bold);
  font-size: var(--jf-text-lg);
  letter-spacing: -0.01em;
}

.brand-mark {
  display: inline-grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
  box-shadow: var(--jf-shadow-sm);
}

.brand-mark i {
  font-size: 1.1rem;
}

.topbar-end {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
}

.theme-toggle {
  display: flex;
  align-items: center;
  gap: 2px;
  border: 1px solid var(--jf-color-border);
  border-radius: 999px;
  padding: 2px;
}

.theme-btn-active {
  background: var(--jf-color-selected) !important;
  color: var(--jf-color-selected-text) !important;
}

.user-profile {
  border: 0;
  background: transparent;
  font: inherit;
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  padding: var(--jf-space-0-5) var(--jf-space-1-5) var(--jf-space-0-5) var(--jf-space-0-5);
  border-radius: 999px;
  cursor: pointer;
  transition: background-color var(--jf-duration);
}

.user-profile:hover {
  background: var(--surface-hover);
}

.user-avatar {
  background: var(--jf-color-text);
  color: var(--jf-color-card);
  font-weight: var(--jf-weight-semibold);
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  color: var(--jf-color-text);
}

.user-name {
  font-weight: var(--jf-weight-semibold);
  font-size: var(--jf-text-sm);
  line-height: var(--jf-leading-tight);
}

.user-profile i {
  color: var(--jf-color-text-muted);
}

:deep(.user-menu) {
  margin-top: var(--jf-space-1);
}

@media print {
  .app-topbar {
    display: none !important;
  }
}
</style>
