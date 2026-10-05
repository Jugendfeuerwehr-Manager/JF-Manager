<template>
  <div class="layout-wrapper">
    <a href="#main-content" class="skip-link">Zum Inhalt springen</a>
    <AppTopbar v-if="!isMobile" />
    <header v-else class="mobile-toolbar">
      <Button icon="pi pi-bars" label="Module" text aria-controls="module-drawer" :aria-expanded="navigationVisible" @click="navigationVisible = true" />
      <router-link to="/" class="mobile-title">{{ websiteTitle }}</router-link>
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

    <Drawer id="module-drawer" v-model:visible="navigationVisible" position="left" class="module-drawer" header="Alle Module">
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
.layout-wrapper { min-height: 100dvh; background: var(--surface-ground); }
.skip-link { position: fixed; top: -100px; left: 1rem; z-index: 2000; padding: .8rem; background: var(--surface-card); color: var(--text-color); }
.skip-link:focus { top: .5rem; }
.desktop-sidebar { position: fixed; top: 70px; left: 0; bottom: 0; width: 232px; overflow-y: auto; background: var(--surface-card); border-right: 1px solid var(--surface-border); z-index: 900; }
.layout-main { margin-left: 232px; padding-top: 70px; min-width: 0; }
.layout-content { padding: 1.5rem; max-width: 1600px; margin: 0 auto; }
.layout-content--full-width { max-width: none; padding: 0; }
.mobile-toolbar { position: fixed; inset: 0 0 auto; height: 60px; z-index: 1000; background: var(--surface-card); border-bottom: 1px solid var(--surface-border); display: flex; align-items: center; justify-content: space-between; padding: 0 .6rem; gap: .5rem; }
.mobile-title { font-weight: 700; font-size: .95rem; color: var(--text-color); text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mobile-bottom-nav { position: fixed; inset: auto 0 0; z-index: 1000; display: flex; justify-content: space-around; background: var(--surface-card); border-top: 1px solid var(--surface-border); padding: .4rem .3rem calc(.4rem + env(safe-area-inset-bottom, 0px)); }
.mobile-bottom-nav a, .mobile-bottom-nav button { display: flex; flex: 1; align-items: center; justify-content: center; flex-direction: column; gap: .4rem; min-height: 48px; color: var(--text-color-secondary); text-decoration: none; font: inherit; font-size: .66rem; border: 0; background: transparent; cursor: pointer; }
.mobile-bottom-nav i { font-size: 1.15rem; }
.mobile-bottom-nav [aria-current="page"], .mobile-bottom-nav [aria-expanded="true"] { color: var(--primary-color); font-weight: 700; }
.drawer-context { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
@media (max-width: 1023px) { .layout-main { margin-left: 0; padding-top: 60px; padding-bottom: calc(76px + env(safe-area-inset-bottom, 0px)); } .layout-content { padding: 1rem; } .layout-content--full-width { padding: 0; } }
@media (max-width: 480px) { .layout-content { padding: .75rem; } .layout-content--full-width { padding: 0; } }
@media print { .desktop-sidebar, .mobile-toolbar, .mobile-bottom-nav, .skip-link { display: none !important; } .layout-main { margin: 0; padding: 0; } .layout-content { max-width: none; padding: 0; } }
</style>
