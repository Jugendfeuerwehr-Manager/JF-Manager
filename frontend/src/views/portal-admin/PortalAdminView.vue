<template>
  <div class="portal-admin">
    <OverviewHeader title="Portal" subtitle="Zugänge, Einladungen, Freigaben und Elternzugriff der Familienportale verwalten" />
    <SegmentedControl :model-value="tab" :options="tabs" label="Bereich der Portalverwaltung" class="tabs" @update:model-value="setTab" />
    <AccessTab v-if="tab === 'zugaenge'" />
    <InvitationsTab v-else-if="tab === 'einladungen'" />
    <ChangeRequestsTab v-else-if="tab === 'antraege'" />
    <ReleasesTab v-else-if="tab === 'freigaben'" />
    <EndingTab v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import AccessTab from './AccessTab.vue'
import ChangeRequestsTab from './ChangeRequestsTab.vue'
import EndingTab from './EndingTab.vue'
import InvitationsTab from './InvitationsTab.vue'
import ReleasesTab from './ReleasesTab.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
// Releases and requests need their own rights; the server answers 403 otherwise (PORTAL-02.3, PORTAL-03).
const tabs = computed(() => [
  { value: 'zugaenge', label: 'Zugänge' },
  { value: 'einladungen', label: 'Einladungen' },
  ...(auth.hasPerm('portal.review_changerequest') ? [{ value: 'antraege', label: 'Anträge' }] : []),
  ...(auth.hasPerm('portal.view_portalpolicy') || auth.hasPerm('portal.change_portalpolicy')
    ? [{ value: 'freigaben', label: 'Freigaben' }]
    : []),
  { value: 'endet', label: 'Elternzugriff endet' },
])
const route = useRoute()
const router = useRouter()
const tab = computed(() => {
  const value = String(route.query.tab ?? '')
  return tabs.value.some(t => t.value === value) ? value : 'zugaenge'
})
function setTab(value: string) { void router.replace({ query: value === 'zugaenge' ? {} : { tab: value } }) }
</script>

<style scoped>
.portal-admin { display: flex; flex-direction: column; gap: var(--jf-space-2); }
.tabs { align-self: flex-start; max-width: 100%; overflow-x: auto; }
</style>
