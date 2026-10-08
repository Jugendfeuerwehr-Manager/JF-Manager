<template>
  <div class="portal-admin">
    <OverviewHeader title="Portal" subtitle="Zugänge, Einladungen und Elternzugriff der Familienportale verwalten" />
    <SegmentedControl :model-value="tab" :options="tabs" label="Bereich der Portalverwaltung" class="tabs" @update:model-value="setTab" />
    <AccessTab v-if="tab === 'zugaenge'" />
    <InvitationsTab v-else-if="tab === 'einladungen'" />
    <EndingTab v-else />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import AccessTab from './AccessTab.vue'
import EndingTab from './EndingTab.vue'
import InvitationsTab from './InvitationsTab.vue'

const tabs = [
  { value: 'zugaenge', label: 'Zugänge' },
  { value: 'einladungen', label: 'Einladungen' },
  { value: 'endet', label: 'Elternzugriff endet' },
]
const route = useRoute()
const router = useRouter()
const tab = computed(() => {
  const value = String(route.query.tab ?? '')
  return tabs.some(t => t.value === value) ? value : 'zugaenge'
})
function setTab(value: string) { void router.replace({ query: value === 'zugaenge' ? {} : { tab: value } }) }
</script>

<style scoped>
.portal-admin { display: flex; flex-direction: column; gap: var(--jf-space-2); }
.tabs { align-self: flex-start; max-width: 100%; overflow-x: auto; }
</style>
