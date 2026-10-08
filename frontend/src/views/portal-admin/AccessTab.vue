<template>
  <section aria-label="Zugänge">
    <div class="toolbar">
      <SegmentedControl :model-value="store.kind" :options="kindOptions" label="Art der Person" @update:model-value="onKind" />
      <label class="search">
        <i class="pi pi-search" aria-hidden="true"></i>
        <input v-model="searchText" type="search" placeholder="Name oder E-Mail suchen …" aria-label="Zugänge durchsuchen" @input="onSearch" />
      </label>
    </div>

    <div class="chips" role="group" aria-label="Nach Zustand filtern">
      <button v-for="chip in chips" :key="chip.value" type="button" class="chip" :aria-pressed="store.stateFilter === chip.value" @click="store.setFilter({ state: chip.value })">
        <i :class="chip.icon" aria-hidden="true"></i><span>{{ chip.label }}</span>
      </button>
    </div>

    <div class="bulk">
      <Button :label="`Ausgewählte einladen (${store.inviteableSelected.length})`" icon="pi pi-send" :disabled="!store.inviteableSelected.length || store.busy" :loading="store.busy" @click="bulk" />
      <Button v-if="store.kind === 'member'" label="Mitglieder einladen" icon="pi pi-send" disabled />
      <small v-if="store.kind === 'member'" class="muted">Mitgliederkonten sind noch nicht freigegeben.</small>
      <small v-else-if="store.selectedCount > store.inviteableSelected.length" class="muted">Nur Personen ohne Zugang oder mit abgelaufener Einladung werden eingeladen.</small>
    </div>

    <StateView v-if="store.loading && !store.records.length" kind="loading" />
    <StateView v-else-if="store.error" kind="error" :message="store.error" @retry="store.loadRecords()" />
    <StateView v-else-if="!store.records.length" kind="empty" title="Keine Treffer" message="Für diese Auswahl gibt es keine Einträge." />
    <ul v-else class="rows" :aria-busy="store.loading">
      <li v-for="record in store.records" :key="`${record.kind}-${record.id}`" class="row">
        <input v-if="record.kind === 'parent'" type="checkbox" class="row__check" :checked="store.selected.includes(record.id)" :aria-label="`${record.name} auswählen`" @change="store.toggleSelected(record.id, ($event.target as HTMLInputElement).checked)" />
        <span v-else class="row__check"></span>
        <div class="row__main">
          <button type="button" class="row__name" @click="openDetail(record)">{{ record.name }}</button>
          <span v-if="record.email" class="row__mail">{{ record.email }}</span>
          <span v-else class="row__mail warn"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> keine E-Mail</span>
          <span v-if="record.children.length" class="row__children">Kinder: {{ record.children.join(', ') }}</span>
        </div>
        <StatusBadge :label="accessStateMeta[record.state].label" :severity="accessStateMeta[record.state].severity" :icon="accessStateMeta[record.state].icon" />
        <div class="row__actions">
          <Button v-for="action in actionsFor(record)" :key="action" :label="actionLabels[action].label" :icon="actionLabels[action].icon" size="small" :severity="action === 'invite' || action === 'resend' || action === 'resume' ? 'primary' : 'secondary'" :outlined="action !== 'invite'" :disabled="store.busy" @click="actions.request(action, rowTarget(record), refreshDetail)" />
        </div>
      </li>
    </ul>

    <Paginator v-if="store.count > store.pageSize" :rows="store.pageSize" :first="store.offset" :total-records="store.count" @page="store.setFilter({ offset: $event.first })" />

    <AccessDetailDialog v-model:visible="detailOpen" @reload="reloadDetail" />

    <Dialog :visible="!!store.bulkResults" modal header="Ergebnis der Einladungen" :style="{ width: '34rem', maxWidth: '96vw' }" @update:visible="store.bulkResults = null">
      <p role="status"><i class="pi pi-send" aria-hidden="true"></i> {{ sentCount }} gesendet, {{ skipped.length }} übersprungen.</p>
      <ul v-if="skipped.length" class="skipped">
        <li v-for="entry in skipped" :key="entry.parent"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> {{ nameOf(entry.parent) }}: {{ entry.detail || skipReason(entry.code) }}</li>
      </ul>
      <template #footer><Button label="Schließen" @click="store.bulkResults = null" /></template>
    </Dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Paginator from 'primevue/paginator'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { AccessKind, AccessRecord, AccessState } from '@/api/portalAdmin'
import { usePortalAdminStore } from '@/stores/portalAdmin'
import AccessDetailDialog from './AccessDetailDialog.vue'
import { accessStateMeta } from './accessState'
import { actionLabels, actionsFor, useAccessActions } from './useAccessActions'

const store = usePortalAdminStore()
const actions = useAccessActions()
const searchText = ref(store.search)
const detailOpen = ref(false)
const current = ref<AccessRecord | null>(null)
let timer: ReturnType<typeof setTimeout> | undefined

const kindOptions: { value: AccessKind, label: string }[] = [{ value: 'parent', label: 'Eltern' }, { value: 'member', label: 'Mitglieder' }]
const chips: { value: AccessState | '', label: string, icon: string }[] = [
  { value: '', label: 'Alle', icon: 'pi pi-list' },
  ...(['none', 'invited', 'expired', 'active', 'suspended'] as AccessState[]).map(value => ({ value, label: accessStateMeta[value].label, icon: accessStateMeta[value].icon })),
]

const skipped = computed(() => store.bulkResults?.filter(r => r.result === 'skipped') ?? [])
const sentCount = computed(() => store.bulkResults?.filter(r => r.result === 'sent').length ?? 0)
const names = ref<Record<number, string>>({})
const nameOf = (id: number) => names.value[id] ?? store.records.find(r => r.id === id)?.name ?? `Person ${id}`
const reasons: Record<string, string> = {
  email_missing: 'keine E-Mail-Adresse hinterlegt', already_linked: 'hat bereits einen Zugang',
  account_exists: 'es besteht bereits ein Konto', invitation_open: 'es ist bereits eine Einladung offen',
}
const skipReason = (code?: string) => (code && reasons[code]) || 'übersprungen'

function onKind(value: AccessKind) { void store.setFilter({ kind: value, state: '' }) }
function onSearch() { clearTimeout(timer); timer = setTimeout(() => { void store.setFilter({ search: searchText.value }) }, 300) }
const rowTarget = (record: AccessRecord) => {
  const invitationId = undefined as number | undefined
  return { kind: record.kind, id: record.id, name: record.name, invitationId }
}
async function bulk() {
  names.value = Object.fromEntries(store.records.map(r => [r.id, r.name]))
  const result = await store.bulkInvite()
  if (!result.ok) actions.report(result, '')
}
function openDetail(record: AccessRecord) {
  current.value = record
  detailOpen.value = true
  void reloadDetail()
}
function reloadDetail() {
  if (current.value) return store.loadDetail(current.value.kind === 'parent' ? { parent: current.value.id } : { member: current.value.id })
}
function refreshDetail() { if (detailOpen.value) void reloadDetail() }

onMounted(() => { void store.loadRecords() })
</script>

<style scoped>
.toolbar, .bulk { display: flex; flex-wrap: wrap; gap: var(--jf-space-1-5); align-items: center; margin-bottom: var(--jf-space-2); }
.search { flex: 1 1 14rem; display: flex; align-items: center; gap: var(--jf-space-1); min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1-5); border: 1px solid var(--p-form-field-border-color); border-radius: var(--jf-radius-md); background: var(--p-form-field-background); color: var(--jf-color-text-muted); }
.search input { flex: 1; min-width: 0; border: 0; background: transparent; color: var(--jf-color-text); font: inherit; }
.search input:focus { outline: 0; }
.search:focus-within { outline: var(--jf-focus-ring); outline-offset: 2px; }
.chips { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); margin-bottom: var(--jf-space-2); }
.chip { display: inline-flex; align-items: center; gap: var(--jf-space-0-5); min-height: var(--jf-touch-target); padding: 0 var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: 999px; background: var(--jf-color-card); color: var(--jf-color-text); font: inherit; cursor: pointer; }
.chip[aria-pressed='true'] { background: var(--jf-color-selected); color: var(--jf-color-selected-text); border-color: var(--jf-color-primary); font-weight: var(--jf-weight-semibold); }
.chip:focus-visible, .row__name:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
.rows { list-style: none; margin: 0; padding: 0; border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-card); }
.row { display: grid; grid-template-columns: 2.75rem minmax(0, 1fr) auto auto; gap: var(--jf-space-1) var(--jf-space-1-5); align-items: center; padding: var(--jf-space-1) var(--jf-space-2); border-bottom: 1px solid var(--jf-color-border); }
.row:last-child { border-bottom: 0; }
.row__check { width: 1.25rem; height: 1.25rem; justify-self: center; }
.row__main { display: flex; flex-direction: column; min-width: 0; }
.row__name { align-self: flex-start; min-height: var(--jf-touch-target); padding: 0; border: 0; background: transparent; color: var(--jf-color-primary); font: inherit; font-weight: var(--jf-weight-semibold); text-align: left; cursor: pointer; }
.row__mail, .row__children { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); overflow-wrap: anywhere; }
.warn { color: var(--p-amber-700); }
.app-dark .warn { color: var(--p-amber-300); }
.row__actions { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); justify-content: flex-end; }
.row__actions :deep(.p-button) { min-height: var(--jf-touch-target); }
.muted { color: var(--jf-color-text-muted); }
.skipped { padding-left: 0; list-style: none; display: flex; flex-direction: column; gap: var(--jf-space-1); }
@media (max-width: 720px) {
  .row { grid-template-columns: 2.75rem minmax(0, 1fr); }
  .row > :nth-child(3) { grid-column: 2; justify-self: start; }
  .row__actions { grid-column: 1 / -1; justify-content: stretch; }
  .row__actions :deep(.p-button) { flex: 1 1 auto; }
}
</style>
