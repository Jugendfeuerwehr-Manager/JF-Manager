<template>
  <nav aria-label="Alle Module" class="module-navigation">
    <label class="nav-search"><i class="pi pi-search" aria-hidden="true"></i><input v-model="search" type="search" placeholder="Modul finden …" aria-label="Module durchsuchen" /></label>
    <section v-for="section in visibleSections" :key="section.label" class="nav-section">
      <h2>{{ section.label }}</h2>
      <router-link v-for="item in section.items" :key="item.to" :to="item.to" class="nav-link" :class="{ active: isActive(item.to) }" :aria-current="isActive(item.to) ? 'page' : undefined" @click="$emit('navigate')">
        <i :class="item.icon" aria-hidden="true"></i><span>{{ item.label }}</span>
      </router-link>
    </section>
    <p v-if="!visibleSections.length" class="nav-empty">Kein passendes Modul gefunden.</p>
  </nav>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
defineEmits<{ navigate: [] }>()
const route = useRoute()
const auth = useAuthStore()
const search = ref('')
interface NavItem { label: string; icon: string; to: string; permission?: string; admin?: boolean }
const sections: { label: string; items: NavItem[] }[] = [
  { label: 'Überblick', items: [{ label: 'Dashboard', icon: 'pi pi-home', to: '/' }] },
  { label: 'Jugendfeuerwehr', items: [
    { label: 'Mitglieder', icon: 'pi pi-users', to: '/members', permission: 'view_member' },
    { label: 'Eltern', icon: 'pi pi-user', to: '/parents', permission: 'view_parent' },
    { label: 'Gruppen', icon: 'pi pi-sitemap', to: '/groups', permission: 'view_group' },
    { label: 'Listen', icon: 'pi pi-list-check', to: '/lists', permission: 'view_memberlist' },
    { label: 'Dienstbuch', icon: 'pi pi-book', to: '/servicebook', permission: 'view_service' },
    { label: 'Ausbildung', icon: 'pi pi-calendar', to: '/training', permission: 'view_trainingsession' },
    { label: 'Qualifikationen', icon: 'pi pi-crown', to: '/qualifications', permission: 'view_qualification' },
  ] },
  { label: 'Organisation', items: [
    { label: 'Inventar', icon: 'pi pi-box', to: '/inventory', permission: 'view_item' },
    { label: 'Bestellungen', icon: 'pi pi-shopping-cart', to: '/orders', permission: 'view_order' },
    { label: 'E-Mails schreiben', icon: 'pi pi-envelope', to: '/emails/compose', permission: 'view_emailmessage' },
    { label: 'E-Mail-Verlauf', icon: 'pi pi-history', to: '/emails/history', permission: 'view_emailmessage' },
  ] },
  { label: 'Verwaltung', items: [
    { label: 'Protokoll', icon: 'pi pi-list', to: '/log', admin: true },
    { label: 'Benutzerverwaltung', icon: 'pi pi-shield', to: '/users', admin: true },
    { label: 'Rollenvorlagen', icon: 'pi pi-id-card', to: '/role-templates', permission: 'view_roletemplate' },
    { label: 'Einstellungen', icon: 'pi pi-cog', to: '/settings', admin: true },
  ] },
]
const visibleSections = computed(() => sections.map(section => ({ ...section, items: section.items.filter(item =>
  (auth.isOrgWide || (!item.admin && (!item.permission || auth.hasPerm(item.permission)))) &&
  item.label.toLocaleLowerCase('de').includes(search.value.trim().toLocaleLowerCase('de'))
) })).filter(section => section.items.length))
function isActive(target: string) { return route.path === target || (target !== '/' && route.path.startsWith(`${target}/`)) }
</script>
<style scoped>
.module-navigation { padding: 1rem .8rem; }
.nav-search { display: flex; align-items: center; gap: .6rem; padding: .7rem; border: 1px solid var(--surface-border); border-radius: 8px; color: var(--text-color-secondary); margin-bottom: 1.5rem; }
.nav-search input { background: transparent; border: 0; color: var(--text-color); width: 100%; min-width: 0; font: inherit; font-size: .85rem; }
.nav-search:focus-within { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.nav-search input:focus { outline: 0; }
.nav-section + .nav-section { margin-top: 1.3rem; }
h2 { margin: 0 .7rem .5rem; color: var(--text-color-secondary); text-transform: uppercase; font-size: .67rem; letter-spacing: .1em; font-weight: 700; }
.nav-link { display: flex; align-items: center; gap: .7rem; min-height: 42px; padding: .6rem .7rem; border-radius: 7px; text-decoration: none; color: var(--text-color); font-size: .86rem; border-left: 3px solid transparent; }
.nav-link i { width: 18px; color: var(--text-color-secondary); }
.nav-link:hover { background: var(--surface-hover); }
.nav-link.active { background: var(--primary-50, #fff0f1); color: var(--primary-color); border-left-color: var(--primary-color); font-weight: 650; }
.nav-link.active i { color: inherit; }
.nav-link:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -2px; }
.nav-empty { color: var(--text-color-secondary); font-size: .85rem; padding: .5rem; }
</style>
