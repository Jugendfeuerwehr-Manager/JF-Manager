<template>
  <section class="change-log" aria-labelledby="change-log-heading">
    <div class="head">
      <i class="pi pi-history" aria-hidden="true"></i>
      <h2 id="change-log-heading">Änderungsverlauf</h2>
    </div>
    <StateView v-if="store.loading" kind="loading" title="Verlauf wird geladen …" class="compact" />
    <StateView v-else-if="store.error" :kind="stateForError(store.error)" class="compact" @retry="reload" />
    <p v-else-if="!store.entries.length" class="muted">Keine protokollierten Änderungen aus dem Portal oder durch die Person selbst.</p>
    <ul v-else class="entries">
      <li v-for="entry in shown" :key="entry.id" class="entry">
        <span class="entry__field">{{ entry.label }}</span>
        <span class="entry__values">{{ entry.old || '–' }} → {{ entry.new || '–' }}</span>
        <span class="entry__meta">
          {{ entry.applied_by || 'Unbekannt' }} · {{ format(entry.applied_at) }}
          <StatusBadge v-if="entry.self_change" label="Eigenänderung" severity="info" icon="pi pi-user-edit" />
          <StatusBadge v-else-if="entry.via_request" label="Antrag" severity="neutral" icon="pi pi-inbox" />
        </span>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import StateView, { stateForError } from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useChangeLogStore } from '@/stores/changeLog'

const props = defineProps<{ kind: 'member' | 'parent', recordId: number }>()
const store = useChangeLogStore()
const shown = computed(() => store.entries.slice(0, 10))
function reload() { void store.load(props.kind, props.recordId) }
watch(() => [props.kind, props.recordId], reload, { immediate: true })
const dateFormat = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
const format = (iso: string) => (iso ? dateFormat.format(new Date(iso)) : '')
</script>

<style scoped>
.change-log { display: flex; flex-direction: column; gap: var(--jf-space-1-5); }
.head { display: flex; align-items: center; gap: var(--jf-space-1); }
.head i { color: var(--jf-color-text-muted); }
h2 { margin: 0; font-size: var(--jf-text-lg); font-weight: var(--jf-weight-semibold); }
.muted { margin: 0; font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.entries { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--jf-space-1-5); }
.entry { display: flex; flex-direction: column; gap: 2px; font-size: var(--jf-text-sm); }
.entry__field { font-weight: var(--jf-weight-semibold); }
.entry__values { overflow-wrap: anywhere; }
.entry__meta { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1); color: var(--jf-color-text-muted); font-size: var(--jf-text-xs); }
.compact { padding: var(--jf-space-2); }
</style>
