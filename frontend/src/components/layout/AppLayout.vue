<template>
  <div class="layout-wrapper">
    <a href="#main-content" class="skip-link">Zum Inhalt springen</a>
    <AppTopbar v-if="!isMobile" />
    <header v-else class="mobile-toolbar">
      <Button icon="pi pi-bars" text rounded aria-label="Alle Module öffnen" aria-controls="module-drawer" :aria-expanded="navigationVisible" @click="navigationVisible = true" />
      <div class="mobile-context">
        <DepartmentSwitcher compact />
        <router-link v-if="!departmentsStore.departments.length" to="/" class="mobile-title">{{ websiteTitle }}</router-link>
      </div>
      <Button icon="pi pi-user" text rounded aria-label="Benutzermenü öffnen" aria-haspopup="menu" @click="toggleUserMenu" />
    </header>

    <aside v-if="!isMobile" class="desktop-sidebar"><ModuleNavigation /></aside>
    <main id="main-content" tabindex="-1" class="layout-main">
      <div class="layout-content" :class="{ 'layout-content--full-width': route.path.startsWith('/settings') }">
        <router-view :key="departmentsStore.activeDepartmentId ?? 'all'" />
      </div>
    </main>

    <nav v-if="isMobile" class="mobile-bottom-nav" aria-label="Schnellzugriff">
      <router-link to="/" :aria-current="route.path === '/' ? 'page' : undefined"><i class="pi pi-home" aria-hidden="true"></i><span>Übersicht</span></router-link>
      <router-link v-if="authStore.canAccessModule('view_member')" to="/members" :aria-current="route.path.startsWith('/members') ? 'page' : undefined"><i class="pi pi-users" aria-hidden="true"></i><span>Mitglieder</span></router-link>
      <router-link v-if="authStore.canAccessModule('view_service')" to="/servicebook" :aria-current="route.path.startsWith('/servicebook') ? 'page' : undefined"><i class="pi pi-book" aria-hidden="true"></i><span>Dienstbuch</span></router-link>
      <button type="button" aria-controls="module-drawer" :aria-expanded="navigationVisible" @click="navigationVisible = true"><i class="pi pi-th-large" aria-hidden="true"></i><span>Alle Module</span></button>
    </nav>

    <Drawer id="module-drawer" v-model:visible="navigationVisible" position="left" class="module-drawer">
      <template #header>
        <span class="drawer-brand"><span class="brand-mark" aria-hidden="true"><i class="pi pi-shield"></i></span>{{ websiteTitle }}</span>
      </template>
      <div class="drawer-context"><DepartmentSwitcher /><Button :icon="themeIcon" text rounded aria-label="Farbschema wechseln" @click="cycleTheme" /></div>
      <ModuleNavigation @navigate="navigationVisible = false" />
      <Button label="Abmelden" icon="pi pi-sign-out" severity="secondary" outlined @click="handleLogout" />
    </Drawer>
    <Menu ref="userMenu" :model="userMenuItems" popup />
    <ConfirmDialog group="session-timeout" />
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useDepartmentsStore } from '@/stores/departments'
import { useAppSettings } from '@/composables/useAppSettings'
import { useTheme } from '@/composables/useTheme'
import AppTopbar from './AppTopbar.vue'
import ModuleNavigation from './ModuleNavigation.vue'
import Button from 'primevue/button'
import Drawer from 'primevue/drawer'
import Menu from 'primevue/menu'
import ConfirmDialog from 'primevue/confirmdialog'
import { useSessionTimeout } from '@/composables/useSessionTimeout'
import DepartmentSwitcher from '@/components/departments/atoms/DepartmentSwitcher.vue'
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const departmentsStore = useDepartmentsStore()
useSessionTimeout()
const { websiteTitle } = useAppSettings()
const { themeMode, setMode } = useTheme()
const userMenu = ref()
const isMobile = ref(window.innerWidth < 1024)
const navigationVisible = ref(false)
const userMenuItems = computed(() => [
  { label: 'Mein Profil', icon: 'pi pi-user', command: () => router.push('/profile') },
  { label: 'Farbschema wechseln', icon: themeIcon.value, command: cycleTheme },
  { separator: true },
  { label: 'Abmelden', icon: 'pi pi-sign-out', command: handleLogout },
])
const themeIcon = computed(() => themeMode.value === 'dark' ? 'pi pi-moon' : themeMode.value === 'light' ? 'pi pi-sun' : 'pi pi-desktop')
function cycleTheme() {
  const modes = ['light', 'dark', 'system'] as const
  setMode(modes[(modes.indexOf(themeMode.value) + 1) % modes.length]!)
}
function toggleUserMenu(event: Event) { userMenu.value.toggle(event) }
function handleLogout() { navigationVisible.value = false; void authStore.logout() }
function handleResize() { isMobile.value = window.innerWidth < 1024; if (!isMobile.value) navigationVisible.value = false }
watch(() => route.path, () => { navigationVisible.value = false })
onMounted(() => { window.addEventListener('resize', handleResize) })
onUnmounted(() => { window.removeEventListener('resize', handleResize) })
</script>
<style scoped>
.layout-wrapper { --topbar-height: 64px; --sidebar-width: 248px; --mobile-bar-height: 56px; min-height: 100dvh; background: var(--jf-color-ground); }
.skip-link { position: fixed; top: -100px; left: var(--jf-space-2); z-index: 2000; padding: var(--jf-space-1) var(--jf-space-2); border-radius: var(--jf-radius-md); background: var(--jf-color-card); color: var(--jf-color-text); box-shadow: var(--jf-shadow-lg); }
.skip-link:focus { top: var(--jf-space-1); }
.desktop-sidebar { position: fixed; top: var(--topbar-height); left: 0; bottom: 0; width: var(--sidebar-width); overflow-y: auto; background: var(--jf-color-card); border-right: 1px solid var(--jf-color-border); z-index: 900; }
.layout-main { margin-left: var(--sidebar-width); padding-top: var(--topbar-height); min-width: 0; }
.layout-main:focus { outline: none; }
.layout-content { padding: var(--jf-space-3) var(--jf-space-4); max-width: 1600px; margin: 0 auto; }
.layout-content--full-width { max-width: none; padding: 0; }
.mobile-toolbar { position: fixed; inset: 0 0 auto; height: var(--mobile-bar-height); z-index: 1000; background: var(--jf-color-card); border-bottom: 1px solid var(--jf-color-border); display: flex; align-items: center; padding: 0 var(--jf-space-0-5); gap: var(--jf-space-0-5); }
.mobile-context { flex: 1; min-width: 0; display: flex; justify-content: center; }
.mobile-context :deep(.department-switcher) { min-width: 0; max-width: 100%; }
.mobile-title { font-weight: var(--jf-weight-bold); font-size: var(--jf-text-md); color: var(--jf-color-text); text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mobile-bottom-nav { position: fixed; inset: auto 0 0; z-index: 1000; display: flex; justify-content: space-around; background: var(--jf-color-card); border-top: 1px solid var(--jf-color-border); padding: var(--jf-space-0-5) var(--jf-space-0-5) calc(var(--jf-space-0-5) + env(safe-area-inset-bottom, 0px)); }
.mobile-bottom-nav a, .mobile-bottom-nav button { display: flex; flex: 1; align-items: center; justify-content: center; flex-direction: column; gap: var(--jf-space-0-5); min-height: 52px; border-radius: var(--jf-radius-md); color: var(--jf-color-text-muted); text-decoration: none; font: inherit; font-size: var(--jf-text-xs); font-weight: var(--jf-weight-medium); border: 0; background: transparent; cursor: pointer; }
.mobile-bottom-nav i { font-size: 1.25rem; }
.mobile-bottom-nav [aria-current="page"], .mobile-bottom-nav [aria-expanded="true"] { color: var(--jf-color-primary); font-weight: var(--jf-weight-bold); }
.mobile-bottom-nav [aria-current="page"] i { background: var(--jf-color-selected); border-radius: 999px; padding: 2px var(--jf-space-2); }
.drawer-brand { display: flex; align-items: center; gap: var(--jf-space-1); font-weight: var(--jf-weight-bold); font-size: var(--jf-text-lg); }
.brand-mark { display: inline-grid; place-items: center; width: 32px; height: 32px; border-radius: var(--jf-radius-md); background: var(--jf-color-primary); color: var(--jf-color-on-primary); }
.drawer-context { display: flex; align-items: center; justify-content: space-between; gap: var(--jf-space-1); }
@media (max-width: 1023px) { .layout-main { margin-left: 0; padding-top: var(--mobile-bar-height); padding-bottom: calc(72px + env(safe-area-inset-bottom, 0px)); } .layout-content { padding: var(--jf-space-2); } .layout-content--full-width { padding: 0; } }
@media (max-width: 480px) { .layout-content { padding: var(--jf-space-1-5); } .layout-content--full-width { padding: 0; } }
@media print { .desktop-sidebar, .mobile-toolbar, .mobile-bottom-nav, .skip-link { display: none !important; } .layout-main { margin: 0; padding: 0; } .layout-content { max-width: none; padding: 0; } }
</style>
