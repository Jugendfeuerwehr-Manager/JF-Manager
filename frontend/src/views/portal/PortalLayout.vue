<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import { brandingApi } from '@/api/branding'
import PortalPersonSwitcher from '@/components/portal/PortalPersonSwitcher.vue'
import { useAuthStore } from '@/stores/auth'
import { usePortalStore } from '@/stores/portal'
import type { PublicBranding } from '@/types/settings'

const auth = useAuthStore()
const portal = usePortalStore()
const branding = ref<PublicBranding | null>(null)
const items = [
  { name: 'portal-home', label: 'Übersicht', icon: 'pi pi-home' },
  { name: 'portal-sessions', label: 'Termine', icon: 'pi pi-calendar' },
  { name: 'portal-data', label: 'Daten', icon: 'pi pi-id-card' },
  { name: 'portal-profile', label: 'Profil', icon: 'pi pi-user' },
]

const firstName = computed(() => portal.me?.account.first_name || auth.user?.first_name || '')
const orgInitials = computed(() => {
  const words = (branding.value?.title || 'JF').split(/\s+/).filter(Boolean)
  return (words.length > 1 ? words.map(w => w.charAt(0)).slice(0, 2).join('') : (words[0] ?? 'JF').slice(0, 2)).toUpperCase()
})

onMounted(() => {
  // Child views fetch first; only fetch here when nothing is loading yet.
  if (!portal.me && !portal.loading) void portal.fetchMe()
  void brandingApi.getPublicBranding().then(r => { branding.value = r.data }).catch(() => undefined)
})
</script>

<template>
  <div class="portal-shell">
    <header class="topbar">
      <div class="topbar-inner">
        <div class="brand">
          <div class="logo" aria-hidden="true">
            <img v-if="branding?.logo_url" :src="branding.logo_url" alt="" />
            <template v-else>{{ orgInitials }}</template>
          </div>
          <div class="brand-text">
            <span class="org">{{ branding?.title }}</span>
            <span class="hello">Hallo{{ firstName ? ` ${firstName}` : '' }}</span>
          </div>
        </div>
        <Button class="logout" icon="pi pi-sign-out" label="Abmelden" text size="small" aria-label="Abmelden" @click="auth.logout()" />
      </div>
      <PortalPersonSwitcher />
    </header>

    <main class="content"><RouterView /></main>

    <nav class="nav" aria-label="Portal">
      <RouterLink v-for="item in items" :key="item.name" :to="{ name: item.name }" class="nav-link" active-class="" exact-active-class="">
        <i :class="item.icon" aria-hidden="true"></i><span>{{ item.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.portal-shell { min-height: 100dvh; display: flex; flex-direction: column; background: var(--p-content-hover-background, var(--p-surface-50)); color: var(--p-text-color); }
.topbar { order: 0; display: flex; flex-direction: column; gap: 12px; padding: 14px 16px 12px; background: var(--p-content-background); border-bottom: 1px solid var(--p-content-border-color); }
.topbar-inner { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.brand { display: flex; align-items: center; gap: 10px; min-width: 0; }
.logo { flex: none; width: 32px; height: 32px; border-radius: 8px; background: var(--p-primary-color); color: var(--p-primary-contrast-color); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; overflow: hidden; }
.logo img { width: 100%; height: 100%; object-fit: contain; }
.brand-text { display: flex; flex-direction: column; min-width: 0; }
.org { font-size: 12px; color: var(--p-text-muted-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hello { font-size: 16px; font-weight: 650; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.logout { display: none; min-height: 44px; }
.content { order: 2; flex: 1; width: 100%; max-width: 40rem; margin: 0 auto; padding: 16px 16px 88px; box-sizing: border-box; }
.nav { order: 3; position: fixed; left: 0; right: 0; bottom: 0; height: 72px; box-sizing: content-box; display: grid; grid-template-columns: repeat(4, 1fr); background: var(--p-content-background); border-top: 1px solid var(--p-content-border-color); padding-bottom: env(safe-area-inset-bottom); z-index: 10; }
.nav-link { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; min-height: 44px; color: var(--p-text-muted-color); text-decoration: none; font-size: 12px; }
.nav-link i { font-size: 22px; }
.nav-link[aria-current='page'] { color: var(--p-primary-color); font-weight: 650; }
.nav-link:focus-visible { outline: 2px solid var(--p-primary-color); outline-offset: -4px; border-radius: 8px; }
@media (min-width: 768px) {
  .topbar { padding-inline: max(16px, calc((100% - 40rem) / 2)); }
  .logout { display: inline-flex; }
  .nav { order: 1; position: static; height: auto; box-sizing: border-box; padding: 0 max(16px, calc((100% - 40rem) / 2)); border-top: none; border-bottom: 1px solid var(--p-content-border-color); }
  .nav-link { flex-direction: row; justify-content: center; gap: 8px; min-height: 48px; font-size: 14px; }
  .nav-link i { font-size: 16px; }
  .nav-link[aria-current='page'] { box-shadow: inset 0 -3px 0 var(--p-primary-color); }
  .content { padding-bottom: 32px; }
}
</style>
