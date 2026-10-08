<template>
  <nav aria-label="Alle Module" class="module-navigation">
    <label class="nav-search"><i class="pi pi-search" aria-hidden="true"></i><input v-model="search" type="search" placeholder="Modul finden …" aria-label="Module durchsuchen" /></label>
    <section v-for="section in visibleSections" :key="section.label" class="nav-section">
      <h2>{{ section.label }}</h2>
      <router-link v-for="item in section.items" :key="item.to" :to="item.to" class="nav-link" :class="{ active: isActive(item.to) }" :aria-current="isActive(item.to) ? 'page' : undefined" @click="$emit('navigate')">
        <i :class="item.icon" aria-hidden="true"></i><span>{{ item.label }}</span>
        <span v-if="item.to === '/eingang' && inbox.counts.total > 0" class="nav-badge" :aria-label="`Eingang, ${inbox.counts.total} offen`">{{ inbox.counts.total }}</span>
      </router-link>
    </section>
    <p v-if="!visibleSections.length" class="nav-empty">Kein passendes Modul gefunden.</p>
  </nav>
</template>
<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useInboxStore } from '@/stores/inbox'
import { useClientConfiguration } from '@/composables/useClientConfiguration'
defineEmits<{ navigate: [] }>()
const { configuration, refresh } = useClientConfiguration()
onMounted(() => { void refresh().catch(() => { /* Existing labels remain usable when offline. */ }) })
const route = useRoute()
const auth = useAuthStore()
const inbox = useInboxStore()
const search = ref('')
const settingsRights = ['all', 'general', 'email', 'member', 'service', 'order', 'ldap', 'oidc'].map(category => `settings_manager.view_${category}_settings`)
interface NavItem { label: string; icon: string; to: string; permission?: string; admin?: boolean }
const sections: { label: string; items: NavItem[] }[] = [
  { label: 'Überblick', items: [{ label: 'Dashboard', icon: 'pi pi-home', to: '/' }, { label: 'Eingang', icon: 'pi pi-inbox', to: '/eingang' }] },
  { label: 'Mitglieder', items: [
    { label: 'Mitglieder', icon: 'pi pi-users', to: '/members', permission: 'view_member' },
    { label: 'Eltern', icon: 'pi pi-user', to: '/parents', permission: 'view_parent' },
    { label: 'Portal', icon: 'pi pi-id-card', to: '/portal-verwaltung', permission: 'portal.invite_portal_account' },
    { label: 'Gruppen', icon: 'pi pi-sitemap', to: '/groups', permission: 'members.view_group' },
    { label: 'Listen', icon: 'pi pi-list-check', to: '/lists', permission: 'view_memberlist' },
  ] },
  { label: 'Dienste', items: [
    { label: 'Dienstbuch', icon: 'pi pi-book', to: '/servicebook', permission: 'view_service' },
    { label: 'Ausbildung', icon: 'pi pi-calendar', to: '/training', permission: 'view_trainingsession' },
    { label: 'Qualifikationen', icon: 'pi pi-crown', to: '/qualifications', permission: 'view_qualification' },
  ] },
  { label: 'Material', items: [
    { label: 'Inventar', icon: 'pi pi-box', to: '/inventory', permission: 'view_item' },
  ] },
  { label: 'Kommunikation', items: [
    { label: 'E-Mails schreiben', icon: 'pi pi-envelope', to: '/emails/compose', permission: 'view_emailmessage' },
    { label: 'E-Mail-Verlauf', icon: 'pi pi-history', to: '/emails/history', permission: 'view_emailmessage' },
  ] },
  { label: 'Verwaltung', items: [
    { label: 'Protokoll', icon: 'pi pi-list', to: '/log', permission: 'members.view_event' },
    { label: 'Benutzerverwaltung', icon: 'pi pi-shield', to: '/users', permission: 'users.view_customuser' },
    { label: 'Rollen und Rechte', icon: 'pi pi-user-edit', to: '/roles' },
    { label: 'Rollenvorlagen', icon: 'pi pi-id-card', to: '/role-templates', permission: 'view_roletemplate' },
    { label: 'Einstellungen', icon: 'pi pi-cog', to: '/settings', permission: 'settings_manager.view_all_settings' },
  ] },
]
const vocabularyLabel = (item: NavItem) => ({ '/members': configuration.member_label, '/servicebook': configuration.service_label, '/training': configuration.training_label }[item.to] || item.label)
const visibleSections = computed(() => sections.map(section => ({ ...section, items: section.items.map(item => ({ ...item, label: vocabularyLabel(item) })).filter(item =>
  (!item.permission || (item.to === '/settings' ? settingsRights.some(permission => auth.hasPerm(permission)) : auth.hasPerm(item.permission))) &&
  item.label.toLocaleLowerCase('de').includes(search.value.trim().toLocaleLowerCase('de'))
) })).filter(section => section.items.length))
function isActive(target: string) { return route.path === target || (target !== '/' && route.path.startsWith(`${target}/`)) }
</script>
<style scoped>
.module-navigation { padding: var(--jf-space-2) var(--jf-space-1-5); }
.nav-search { display: flex; align-items: center; gap: var(--jf-space-1); min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1-5); border: 1px solid var(--p-form-field-border-color); border-radius: var(--jf-radius-md); background: var(--p-form-field-background); color: var(--jf-color-text-muted); margin-bottom: var(--jf-space-3); }
.nav-search input { background: transparent; border: 0; color: var(--jf-color-text); width: 100%; min-width: 0; font: inherit; font-size: var(--jf-text-sm); }
.nav-search input::placeholder { color: var(--p-form-field-placeholder-color); }
.nav-search:focus-within { outline: var(--jf-focus-ring); outline-offset: 2px; }
.nav-search input:focus { outline: 0; }
.nav-section + .nav-section { margin-top: var(--jf-space-3); }
h2 { margin: 0 var(--jf-space-1-5) var(--jf-space-1); color: var(--jf-color-text-muted); text-transform: uppercase; font-size: var(--jf-text-xs); letter-spacing: 0.08em; font-weight: var(--jf-weight-bold); }
.nav-link { position: relative; display: flex; align-items: center; gap: var(--jf-space-1-5); min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1-5); border-radius: var(--jf-radius-md); text-decoration: none; color: var(--jf-color-text); font-size: var(--jf-text-sm); font-weight: var(--jf-weight-medium); transition: background-color var(--jf-duration); }
.nav-link + .nav-link { margin-top: 2px; }
.nav-link i { width: 18px; text-align: center; color: var(--jf-color-text-muted); }
.nav-link:hover { background: var(--surface-hover); }
.nav-link.active { background: var(--jf-color-selected); color: var(--jf-color-selected-text); font-weight: var(--jf-weight-semibold); }
.nav-link.active::before { content: ''; position: absolute; left: 0; top: 10px; bottom: 10px; width: 3px; border-radius: 0 3px 3px 0; background: var(--jf-color-primary); }
.nav-link.active i { color: var(--jf-color-primary); }
.nav-link:focus-visible { outline: var(--jf-focus-ring); outline-offset: -2px; }
.nav-badge { margin-left: auto; min-width: 22px; height: 22px; padding: 0 6px; border-radius: 11px; display: inline-flex; align-items: center; justify-content: center; background: var(--jf-color-primary); color: var(--jf-color-on-primary); font-size: var(--jf-text-xs); font-weight: var(--jf-weight-bold); }
.nav-empty { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); padding: var(--jf-space-1); }
</style>
