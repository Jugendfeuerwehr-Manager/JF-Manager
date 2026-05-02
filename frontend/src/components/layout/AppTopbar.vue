<template>
  <div class="app-topbar">
    <Menubar :model="menuItems" class="topbar-menubar">
      <template #start>
        <div class="logo" @click="$router.push('/')">
          <i class="pi pi-shield"></i>
          <span class="logo-text">{{ websiteTitle }}</span>
        </div>
      </template>

      <template #end>
        <div class="topbar-end">
          <!-- Department switcher -->
          <DepartmentSwitcher />
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
        </div>
      </template>
    </Menubar>
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
import Menubar from 'primevue/menubar'
import type { MenuItem } from 'primevue/menuitem'
import DepartmentSwitcher from '@/components/departments/atoms/DepartmentSwitcher.vue'

const emit = defineEmits<{
  menuClick : []
}>()

const router = useRouter()
const authStore = useAuthStore()
const { websiteTitle } = useAppSettings()
const { themeMode, setMode } = useTheme()
const userMenu = ref()

const createNavItem = (label: string, icon: string, to: string): MenuItem => ({
  label,
  icon,
  to,
  command: () => router.push(to)
})

/** All possible top-bar quick-nav items with their required view permission. */
interface PermissionedNavItem extends MenuItem {
  viewPerm?: string   // bare codename, e.g. 'view_member'
  staffOnly?: boolean
}

const allTopbarItems: PermissionedNavItem[] = [
  { ...createNavItem('Mitglieder', 'pi pi-users', '/members'), viewPerm: 'view_member' },
  { ...createNavItem('Eltern', 'pi pi-user', '/parents'), viewPerm: 'view_parent' },
  { ...createNavItem('Dienstbuch', 'pi pi-book', '/servicebook'), viewPerm: 'view_service' },
]

const menuItems = computed<MenuItem[]>(() => {
  const visible = allTopbarItems.filter(item => {
    if (authStore.isOrgWide) return true
    if (item.viewPerm) return authStore.hasPerm(item.viewPerm)
    return true
  })
  return [
    ...visible,
    {
      label: 'Mehr',
      icon: 'pi pi-ellipsis-h',
      command: () => emit('menuClick')
    }
  ]
})

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
    command: () => authStore.logout()
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
  height: 70px;
  background: var(--p-menu-background);
  border-bottom: 1px solid var(--p-menu-border-color);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.topbar-menubar {
  height: 100%;
  border: none;
  background: transparent;
  padding: 0 1.5rem;
  max-width: 1600px;
  margin: 0 auto;
}

:deep(.p-menubar-root-list) {
  gap: 0.25rem;
}

.logo {
  display: flex;
  align-items: center;
  cursor: pointer;
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

.topbar-end {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.theme-toggle {
  display: flex;
  align-items: center;
  gap: 0.1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius-md);
  padding: 0.1rem;
}

.theme-btn-active {
  background: var(--p-primary-50) !important;
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

.user-profile i {
  color: var(--text-color-secondary);
  margin-left: 0.5rem;
}

:deep(.user-menu) {
  margin-top: 0.5rem;
}

@media print {
  .app-topbar {
    display: none !important;
  }
}
</style>
