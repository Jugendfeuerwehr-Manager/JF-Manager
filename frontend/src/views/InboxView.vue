<template>
  <div class="inbox">
    <OverviewHeader title="Eingang" :subtitle="summary">
      <template #actions>
        <Button label="Als gelesen markieren" icon="pi pi-check" severity="secondary" outlined :disabled="!store.selected.length" :badge="store.selected.length ? String(store.selected.length) : undefined" @click="readSelected" />
      </template>
    </OverviewHeader>

    <section class="inbox-filters" aria-label="Filter">
      <SegmentedControl :model-value="store.filters.type ?? ''" label="Art" :options="typeOptions" @update:model-value="v => store.setFilters({ type: v })" />
      <SegmentedControl :model-value="store.filters.category ?? ''" label="Kategorie" :options="categoryOptions" @update:model-value="v => store.setFilters({ category: v })" />
      <Select v-if="departments.length > 1" :model-value="store.filters.department" :options="departments" option-label="name" option-value="id" show-clear filter placeholder="Alle Abteilungen" aria-label="Abteilung" class="inbox-department" @update:model-value="v => store.setFilters({ department: v ?? null })" />
      <label class="inbox-toggle"><input type="checkbox" :checked="store.filters.unread" @change="store.setFilters({ unread: ($event.target as HTMLInputElement).checked })" />Nur ungelesen</label>
      <label class="inbox-toggle"><input type="checkbox" :checked="store.filters.done" @change="store.setFilters({ done: ($event.target as HTMLInputElement).checked })" />Erledigte anzeigen</label>
    </section>

    <p v-if="actionError" class="inbox-error" role="alert">{{ actionError }}</p>
    <StateView v-if="store.loading && !store.entries.length" kind="loading" title="Eingang wird geladen …" />
    <StateView v-else-if="store.error && !store.entries.length" kind="error" :message="store.error" @retry="store.fetchEntries()" />
    <StateView v-else-if="!store.entries.length" kind="empty" :title="filtered ? 'Keine passenden Einträge' : 'Alles erledigt'" :message="filtered ? 'Mit diesen Filtern gibt es keine Einträge. Filter anpassen, um mehr zu sehen.' : 'Neue Aufgaben und Hinweise zu Anträgen, Meldungen, Besetzung und Konten erscheinen hier.'" />
    <template v-else>
      <section v-for="group in groups" :key="group.type" class="inbox-group" :aria-labelledby="`inbox-${group.type}`">
        <h2 :id="`inbox-${group.type}`">{{ group.title }}</h2>
        <ul class="inbox-list">
          <li v-for="entry in group.entries" :key="entry.id" class="inbox-card" :class="{ 'inbox-card--unread': !entry.read, 'inbox-card--done': entry.task_state === 'done' }">
            <input v-if="!entry.read" type="checkbox" class="inbox-select" :checked="store.selected.includes(entry.id)" :aria-label="`${entry.title} auswählen`" @change="store.toggleSelected(entry.id)" />
            <span v-else class="inbox-select-spacer" aria-hidden="true"></span>
            <div class="inbox-body">
              <div class="inbox-meta">
                <span class="inbox-type"><i :class="entry.type === 'task' ? 'pi pi-bolt' : 'pi pi-info-circle'" aria-hidden="true"></i>{{ entry.type === 'task' ? 'Aufgabe' : 'Hinweis' }}</span>
                <span class="inbox-category">{{ categoryLabel(entry.category) }}</span>
                <span class="inbox-time">{{ [entry.department, relativeTime(entry.updated_at)].filter(Boolean).join(' · ') }}</span>
              </div>
              <span class="inbox-title">
                <span v-if="!entry.read" class="inbox-dot" aria-hidden="true"></span>
                <span v-if="!entry.read" class="sr-only">Ungelesen: </span>{{ entry.title }}
              </span>
              <span v-if="entry.type === 'notice' && entry.count > 1" class="inbox-sub">{{ entry.count }} Meldungen gebündelt, zuletzt {{ relativeTime(entry.updated_at) }}</span>
              <span v-if="entry.task_state === 'done'" class="inbox-done"><i class="pi pi-check-circle" aria-hidden="true"></i>{{ doneText(entry) }}</span>
            </div>
            <div class="inbox-actions">
              <Button v-if="entry.link" label="Öffnen" size="small" :severity="entry.task_state === 'open' ? undefined : 'secondary'" :outlined="entry.task_state !== 'open'" @click="open(entry)" />
              <Button v-if="entry.task_state === 'open'" label="Als erledigt markieren" size="small" severity="secondary" outlined :loading="busy === entry.id" @click="done(entry)" />
            </div>
          </li>
        </ul>
      </section>
      <Button v-if="store.hasMore" label="Mehr laden" severity="secondary" outlined :loading="store.loading" class="inbox-more" @click="store.fetchEntries(true)" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Select from 'primevue/select'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import StateView from '@/components/common/StateView.vue'
import { useInboxStore } from '@/stores/inbox'
import { useDepartmentsStore } from '@/stores/departments'
import { getApiErrorMessage } from '@/utils/apiError'
import { categoryLabel, doneText, relativeTime } from '@/utils/inbox'
import type { InboxCategory, InboxEntry, InboxType } from '@/api/inbox'

const store = useInboxStore()
const departments = computed(() => useDepartmentsStore().departments)
const router = useRouter()
const busy = ref<number | null>(null)
const actionError = ref('')

const typeOptions: { value: InboxType | '', label: string }[] = [
  { value: '', label: 'Alle' }, { value: 'task', label: 'Aufgaben' }, { value: 'notice', label: 'Hinweise' },
]
const categoryOptions: { value: InboxCategory | '', label: string }[] = [
  { value: '', label: 'Alle Kategorien' }, { value: 'requests', label: 'Anträge' }, { value: 'registrations', label: 'Meldungen' },
  { value: 'staffing', label: 'Besetzung' }, { value: 'accounts', label: 'Konten' },
]

const summary = computed(() => {
  const { open_tasks: tasks, unread_notices: notices } = store.counts
  return `${tasks} offene ${tasks === 1 ? 'Aufgabe' : 'Aufgaben'} · ${notices} ungelesene ${notices === 1 ? 'Hinweis' : 'Hinweise'}`
})
const filtered = computed(() => !!(store.filters.type || store.filters.category || store.filters.department || store.filters.unread || store.filters.done))
const groups = computed(() => [
  { type: 'task', title: 'Aufgaben', entries: store.entries.filter(e => e.type === 'task') },
  { type: 'notice', title: 'Hinweise', entries: store.entries.filter(e => e.type === 'notice') },
].filter(group => group.entries.length))

async function attempt(action: () => Promise<unknown>) {
  actionError.value = ''
  try { await action() } catch (err) { actionError.value = getApiErrorMessage(err, 'Die Aktion konnte nicht ausgeführt werden.') }
}
async function open(entry: InboxEntry) {
  if (!entry.read) await attempt(() => store.markRead(entry.id))
  void router.push(entry.link)
}
async function done(entry: InboxEntry) {
  busy.value = entry.id
  await attempt(() => store.markDone(entry.id))
  busy.value = null
}
const readSelected = () => attempt(() => store.markReadBulk())

onMounted(() => {
  void store.fetchEntries()
  void store.fetchCounts()
  if (!useDepartmentsStore().departments.length) void useDepartmentsStore().fetchDepartments()
})
</script>

<style scoped>
.inbox { display: flex; flex-direction: column; gap: var(--jf-space-3); }
.inbox-filters { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-2); }
.inbox-department { min-width: 14rem; }
.inbox-toggle { display: flex; align-items: center; gap: var(--jf-space-1); min-height: var(--jf-touch-target); font-size: var(--jf-text-sm); }
.inbox-toggle input, .inbox-select { width: 18px; height: 18px; }
.inbox-error { margin: 0; color: var(--jf-color-danger-text, var(--jf-color-text)); }
.inbox-group h2 { margin: 0 0 var(--jf-space-1); font-size: var(--jf-text-xs); text-transform: uppercase; letter-spacing: 0.05em; color: var(--jf-color-text-muted); font-weight: var(--jf-weight-bold); }
.inbox-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--jf-space-1-5); }
.inbox-card { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1-5); padding: var(--jf-space-2); background: var(--jf-color-card); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg, var(--jf-radius-md)); }
.inbox-card--done { opacity: 0.8; }
.inbox-select-spacer { width: 18px; flex: none; }
.inbox-body { flex: 1 1 18rem; min-width: 0; display: flex; flex-direction: column; gap: var(--jf-space-0-5, 4px); }
.inbox-meta { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1); font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }
.inbox-type { display: inline-flex; align-items: center; gap: 4px; font-weight: var(--jf-weight-semibold); color: var(--jf-color-text); }
.inbox-category { padding: 2px var(--jf-space-1); border-radius: var(--jf-radius-sm, 6px); background: var(--jf-color-selected); color: var(--jf-color-selected-text); font-weight: var(--jf-weight-semibold); }
.inbox-title { display: flex; align-items: center; gap: var(--jf-space-1); font-weight: var(--jf-weight-semibold); }
.inbox-card--unread .inbox-title { font-weight: var(--jf-weight-bold); }
.inbox-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--jf-color-primary); flex: none; }
.inbox-sub, .inbox-done { font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.inbox-done { display: inline-flex; align-items: center; gap: 6px; }
.inbox-actions { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); }
.inbox-more { align-self: center; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
@media (max-width: 640px) {
  .inbox-actions { width: 100%; }
  .inbox-actions :deep(.p-button) { flex: 1 1 auto; min-height: var(--jf-touch-target); }
  .inbox-department { width: 100%; }
}
</style>
