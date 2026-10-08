<template>
  <section aria-label="Elternzugriff endet">
    <p class="lead">Kinder, deren Elternzugriff bald endet oder bereits beendet ist. Eine Verlängerung ist begründet und höchstens 12 Monate nach dem 18. Geburtstag möglich.</p>
    <StateView v-if="store.endingLoading && !store.ending.length" kind="loading" />
    <StateView v-else-if="store.endingError" kind="error" :message="store.endingError" @retry="store.loadEnding()" />
    <StateView v-else-if="!store.ending.length" kind="empty" title="Nichts zu tun" message="Aktuell endet kein Elternzugriff in absehbarer Zeit." />
    <ul v-else class="rows">
      <li v-for="entry in store.ending" :key="`${entry.parent}-${entry.member}`" class="row">
        <div class="row__main">
          <strong>{{ entry.name }}</strong>
          <span class="meta">Elternteil: {{ entry.parent_name }}</span>
          <span class="meta">
            {{ entry.ended ? 'Elternzugriff endete am' : 'Elternzugriff bis' }} {{ formatDate(entry.access_ends_on) }}
            <template v-if="entry.extended_until"> · verlängert bis {{ formatDate(entry.extended_until) }}</template>
          </span>
        </div>
        <StatusBadge v-if="entry.ended" label="Beendet" severity="danger" icon="pi pi-ban" />
        <StatusBadge v-else label="Endet bald" severity="warning" />
        <Button label="Verlängern" icon="pi pi-calendar-plus" size="small" severity="secondary" outlined @click="open(entry)" />
      </li>
    </ul>
    <ExtendDialog v-model:visible="dialog" :target="target" @done="onDone" />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { EndingEntry } from '@/api/portalAdmin'
import { usePortalAdminStore } from '@/stores/portalAdmin'
import ExtendDialog, { type ExtendTarget } from './ExtendDialog.vue'
import { formatDate } from './accessState'

const store = usePortalAdminStore()
const toast = useToast()
const dialog = ref(false)
const target = ref<ExtendTarget | null>(null)

function open(entry: EndingEntry) {
  target.value = { parent: entry.parent, parentName: entry.parent_name, member: entry.member, name: entry.name, endsOn: entry.extended_until ?? entry.access_ends_on }
  dialog.value = true
}
function onDone() { toast.add({ severity: 'success', summary: 'Elternzugriff verlängert.', life: 4000 }) }
onMounted(() => { void store.loadEnding() })
</script>

<style scoped>
.lead { margin: 0 0 var(--jf-space-2); color: var(--jf-color-text-muted); }
.rows { list-style: none; margin: 0; padding: 0; border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-card); }
.row { display: flex; flex-wrap: wrap; gap: var(--jf-space-1) var(--jf-space-2); align-items: center; padding: var(--jf-space-1-5) var(--jf-space-2); border-bottom: 1px solid var(--jf-color-border); }
.row:last-child { border-bottom: 0; }
.row__main { flex: 1 1 16rem; display: flex; flex-direction: column; min-width: 0; }
.meta { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.row :deep(.p-button) { min-height: var(--jf-touch-target); }
</style>
