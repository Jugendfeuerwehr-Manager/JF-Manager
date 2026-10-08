<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import { brandingApi } from '@/api/branding'
import { useAuthStore } from '@/stores/auth'
import type { PublicBranding } from '@/types/settings'

const auth = useAuthStore()
const branding = ref<PublicBranding | null>(null)
const items = [
  { name: 'portal-home', label: 'Übersicht', icon: 'pi pi-home', exact: true },
  { name: 'portal-sessions', label: 'Termine', icon: 'pi pi-calendar', exact: false },
  { name: 'portal-data', label: 'Daten', icon: 'pi pi-id-card', exact: false },
  { name: 'portal-profile', label: 'Profil', icon: 'pi pi-user', exact: false },
]

onMounted(() => {
  void brandingApi.getPublicBranding().then(r => { branding.value = r.data }).catch(() => undefined)
})
</script>

<template>
  <div class="portal-shell">
    <header class="topbar">
      <div class="brand">
        <img v-if="branding?.logo_url" :src="branding.logo_url" :alt="`Logo ${branding.title || ''}`" />
        <span class="title">{{ branding?.title }}</span>
      </div>
      <nav class="nav nav-wide" aria-label="Portal">
        <RouterLink v-for="item in items" :key="item.name" :to="{ name: item.name }" class="nav-link" active-class="" exact-active-class="">
          <i :class="item.icon" aria-hidden="true"></i><span>{{ item.label }}</span>
        </RouterLink>
      </nav>
      <div class="account">
        <span class="name">{{ auth.userFullName }}</span>
        <Button icon="pi pi-sign-out" label="Abmelden" text size="small" class="touch" aria-label="Abmelden" @click="auth.logout()" />
      </div>
    </header>

    <main class="content"><RouterView /></main>

    <nav class="nav nav-tabs" aria-label="Portal">
      <RouterLink v-for="item in items" :key="item.name" :to="{ name: item.name }" class="nav-link" active-class="" exact-active-class="">
        <i :class="item.icon" aria-hidden="true"></i><span>{{ item.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.portal-shell { min-height: 100dvh; display: flex; flex-direction: column; background: var(--p-content-hover-background, var(--p-surface-50)); color: var(--p-text-color); }
.topbar { display: flex; align-items: center; gap: 0.75rem; padding: 0.25rem 0.75rem; min-height: 56px; background: var(--p-content-background); border-bottom: 1px solid var(--p-content-border-color); }
.brand { display: flex; align-items: center; gap: 0.5rem; min-width: 0; flex: 1; }
.brand img { height: 32px; width: auto; }
.title { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.account { display: flex; align-items: center; gap: 0.25rem; }
.name { display: none; color: var(--p-text-muted-color); }
.touch { min-height: 44px; min-width: 44px; }
.content { flex: 1; width: 100%; max-width: 60rem; margin: 0 auto; padding: 1rem 1rem 5.5rem; box-sizing: border-box; }
.nav-link { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.15rem; min-height: 44px; min-width: 44px; padding: 0.25rem 0.5rem; color: var(--p-text-muted-color); text-decoration: none; font-size: 0.75rem; border-radius: 0.5rem; }
.nav-link i { font-size: 1.25rem; }
.nav-link[aria-current='page'] { color: var(--p-primary-color); font-weight: 700; box-shadow: inset 0 -3px 0 var(--p-primary-color); }
.nav-tabs { position: fixed; left: 0; right: 0; bottom: 0; display: grid; grid-template-columns: repeat(4, 1fr); background: var(--p-content-background); border-top: 1px solid var(--p-content-border-color); padding-bottom: env(safe-area-inset-bottom); }
.nav-tabs .nav-link { min-height: 56px; }
.nav-wide { display: none; }
@media (min-width: 768px) {
  .nav-tabs { display: none; }
  .nav-wide { display: flex; gap: 0.25rem; }
  .nav-wide .nav-link { flex-direction: row; gap: 0.5rem; font-size: 0.95rem; padding: 0.5rem 0.9rem; }
  .nav-wide .nav-link i { font-size: 1rem; }
  .name { display: inline; }
  .brand { flex: 0 1 auto; }
  .content { padding-bottom: 2rem; }
  .account { margin-left: auto; }
}
</style>
