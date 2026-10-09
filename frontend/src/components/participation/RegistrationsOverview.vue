<template>
  <div class="reg-overview">
    <p v-if="store.registrationsLoading && !data" role="status"><i class="pi pi-spin pi-spinner" aria-hidden="true"></i> Meldungen werden geladen …</p>
    <div v-else-if="!data" role="alert">
      <p>{{ store.registrationsError ?? 'Die Meldungen sind nicht verfügbar.' }}</p>
      <Button label="Erneut laden" severity="secondary" @click="store.loadRegistrations(sessionId)" />
    </div>
    <template v-else>
      <p v-if="store.registrationsError" class="reg-overview__error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ store.registrationsError }}</p>
      <ul class="reg-overview__counts" aria-label="Zusammenfassung">
        <li v-for="item in countItems" :key="item.key"><StatusBadge :label="`${item.label}: ${item.value}`" :severity="item.severity" :icon="item.icon" /></li>
        <li v-if="data.counts.conflicts > 0"><StatusBadge :label="`Voraussetzung nicht mehr erfüllt: ${data.counts.conflicts}`" severity="warning" icon="pi pi-exclamation-triangle" /></li>
        <li v-if="data.counts.max_participants !== null">Plätze: {{ data.counts.seated }} von {{ data.counts.max_participants }} belegt<template v-if="data.counts.free !== null">, {{ data.counts.free }} frei</template></li>
        <li v-if="data.staffing?.required && data.slots?.length"><StatusBadge :label="data.staffing.text" :severity="data.staffing.met ? 'success' : 'warning'" :icon="data.staffing.met ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'" /></li>
        <li v-if="data.counts.min_participants && !data.slots?.length">Mindestzahl: {{ data.counts.min_participants }}<template v-if="data.counts.seated < data.counts.min_participants"> (noch nicht erreicht)</template></li>
      </ul>
      <p class="reg-overview__deadlines">
        Anmeldeschluss {{ formatDateTime(data.deadlines.registration_closes_at) }} · Abmeldeschluss {{ formatDateTime(data.deadlines.cancellation_closes_at) }}
      </p>
      <p v-if="data.truncated" class="reg-overview__error" role="status">Die Zielgruppe ist sehr groß; es werden nicht alle Personen aufgeführt.</p>

      <div class="reg-overview__filter">
        <label for="reg-filter">Anzeigen</label>
        <select id="reg-filter" v-model="filter" class="reg-input">
          <option value="all">Alle ({{ visibleRows.length }})</option>
          <option value="open">Ohne Rückmeldung ({{ countOf(openStates) }})</option>
          <option value="in">Angemeldet oder zugeteilt ({{ countOf(['registered', 'assigned']) }})</option>
          <option value="waiting">Warteliste, Bewerbungen ({{ countOf(['waitlisted', 'applied']) }})</option>
          <option value="out">Abgemeldet ({{ countOf(['cancelled', 'not_selected']) }})</option>
        </select>
        <Button icon="pi pi-refresh" label="Aktualisieren" severity="secondary" text :loading="store.registrationsLoading" @click="store.loadRegistrations(sessionId)" />
      </div>

      <p v-if="actionError" class="reg-overview__error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ actionError }}</p>

      <p v-if="!rows.length" class="reg-overview__empty">Keine Personen in dieser Ansicht.</p>
      <table v-else class="reg-table">
        <caption class="sr-only">Meldungen zu diesem Dienst</caption>
        <thead>
          <tr><th scope="col">Person</th><th scope="col">Status</th><th scope="col">Hinweis</th><th scope="col" class="reg-table__actions">Aktion</th></tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.member_id">
            <th scope="row">{{ row.name }} {{ row.lastname }}<span v-if="!row.in_target" class="reg-note"> (nicht mehr in der Zielgruppe)</span></th>
            <td>
              <StatusBadge v-bind="stateLabel(row.state, row.waitlist_position)" />
              <div v-if="positionText(row)" class="reg-note">{{ positionText(row) }}</div>
              <div v-if="row.registration?.reason_category" class="reg-note">{{ reasonLabel(row.registration.reason_category) }}</div>
              <div v-if="row.registration?.reason_note" class="reg-note">{{ row.registration.reason_note }}</div>
            </td>
            <td>
              <ul class="reg-hints">
                <li v-if="row.registration?.late"><i class="pi pi-clock" aria-hidden="true"></i>Nach Frist erfasst</li>
                <li v-if="row.registration?.conflict"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i>Voraussetzung nicht mehr erfüllt: {{ row.registration.conflict_reasons.join('; ') }}</li>
                <li v-else-if="!row.eligibility.ok"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i>Voraussetzungen nicht erfüllt: {{ row.eligibility.reasons.join('; ') }}</li>
              </ul>
            </td>
            <td class="reg-table__actions">
              <template v-if="canManage">
                <Button
                  v-if="data.mode !== 'assignment' && row.state !== 'registered'"
                  label="Anmelden"
                  icon="pi pi-check"
                  size="small"
                  severity="secondary"
                  :aria-label="`${row.name} ${row.lastname} anmelden`"
                  :loading="store.busyMember === row.member_id"
                  :disabled="store.busyMember !== null"
                  @click="register(row)"
                />
                <Button
                  v-if="row.state !== 'cancelled' && row.state !== 'not_selected'"
                  label="Abmelden"
                  icon="pi pi-times"
                  size="small"
                  severity="secondary"
                  outlined
                  :aria-label="`${row.name} ${row.lastname} abmelden`"
                  :disabled="store.busyMember !== null"
                  @click="askCancel(row)"
                />
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </template>

    <Dialog v-model:visible="cancelling" modal header="Abmeldung erfassen" :style="{ width: '28rem', maxWidth: 'calc(100vw - 24px)' }">
      <div v-if="cancelTarget" class="reg-cancel">
        <p>{{ cancelTarget.name }} {{ cancelTarget.lastname }} abmelden.</p>
        <label for="reg-reason">Grund</label>
        <select id="reg-reason" v-model="reason" class="reg-input">
          <option v-for="option in REASON_OPTIONS" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
        <label for="reg-reason-note">Kurzer Hinweis (optional)</label>
        <input id="reg-reason-note" v-model="reasonNote" class="reg-input" maxlength="200">
      </div>
      <template #footer>
        <Button label="Abbrechen" severity="secondary" text @click="cancelling = false" />
        <Button label="Abmelden" icon="pi pi-check" :loading="store.busyMember !== null" @click="confirmCancel" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useParticipationStore } from '@/stores/participation'
import type { DisplayState, ReasonCategory, RegistrationRow } from '@/api/participation'
import { REASON_OPTIONS, reasonLabel, stateLabel } from './registrationLabels'

const props = defineProps<{ sessionId: number, canManage?: boolean }>()
const store = useParticipationStore()
const data = computed(() => store.registrations)

const openStates: DisplayState[] = ['no_response', 'expected']
const filter = ref<'all' | 'open' | 'in' | 'waiting' | 'out'>('all')
const filterStates: Record<string, DisplayState[]> = {
  open: openStates, in: ['registered', 'assigned'], waiting: ['waitlisted', 'applied'], out: ['cancelled', 'not_selected'],
}
// Members outside the target group only matter while they still hold a registration.
const visibleRows = computed(() => (data.value?.members ?? []).filter(row => row.in_target || row.registration))
const rows = computed(() => filter.value === 'all' ? visibleRows.value : visibleRows.value.filter(row => filterStates[filter.value]!.includes(row.state)))
const countOf = (states: DisplayState[]) => visibleRows.value.filter(row => states.includes(row.state)).length

const countItems = computed(() => {
  const counts = data.value?.counts
  if (!counts) return []
  const item = (key: DisplayState, label: string, value: number) => { const { severity, icon } = stateLabel(key); return { key, label, value, severity, icon } }
  const items = [
    item('registered', 'Angemeldet', counts.registered ?? 0),
    item('waitlisted', 'Warteliste', counts.waitlisted ?? 0),
    item('applied', 'Beworben', counts.applied ?? 0),
    item('assigned', 'Zugeteilt', counts.assigned ?? 0),
    item('cancelled', 'Abgemeldet', counts.cancelled ?? 0),
    item('expected', 'Erwartet', counts.expected ?? 0),
    item('no_response', 'Keine Rückmeldung', counts.no_response ?? 0),
  ]
  return items.filter(item => item.value > 0 || ['registered', 'cancelled'].includes(item.key))
})

const slotName = (id: number | null | undefined) => data.value?.slots?.find(slot => slot.id === id)?.label ?? null

/** "Position: Wachführung", "ohne Position", or the wished/asked position while waiting. */
function positionText(row: RegistrationRow): string | null {
  if (!data.value?.slots?.length || !row.registration) return null
  if (row.state === 'registered' || row.state === 'assigned') return `Position: ${slotName(row.registration.slot) ?? 'ohne Position'}`
  if (row.state === 'waitlisted' || row.state === 'applied') {
    const wish = slotName(row.registration.preferred_slot)
    return wish ? `${row.state === 'applied' ? 'Wunsch' : 'Wartet auf'}: ${wish}` : (row.state === 'applied' ? 'Wunsch: beliebige passende Position' : 'Wartet auf: beliebige Position')
  }
  return null
}

const actionError = ref<string | null>(null)
const cancelling = ref(false)
const cancelTarget = ref<RegistrationRow | null>(null)
const reason = ref<ReasonCategory>('')
const reasonNote = ref('')

const formatDateTime = (iso: string | null) => iso
  ? new Date(iso).toLocaleString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  : '–'

async function register(row: RegistrationRow) {
  actionError.value = null
  const result = await store.setRegistration(row.member_id, 'registered')
  if (!result.ok) actionError.value = result.message ?? 'Die Meldung konnte nicht geändert werden.'
}
function askCancel(row: RegistrationRow) {
  cancelTarget.value = row
  reason.value = ''
  reasonNote.value = ''
  cancelling.value = true
}
async function confirmCancel() {
  if (!cancelTarget.value) return
  actionError.value = null
  const result = await store.setRegistration(cancelTarget.value.member_id, 'cancelled', { category: reason.value, note: reasonNote.value.trim() })
  cancelling.value = false
  if (!result.ok) actionError.value = result.message ?? 'Die Meldung konnte nicht geändert werden.'
}

onMounted(() => { void store.loadRegistrations(props.sessionId) })
watch(() => props.sessionId, id => { void store.loadRegistrations(id) })
</script>

<style scoped>
.reg-overview { display: grid; gap: var(--jf-space-1-5); }
.reg-overview p { margin: 0; }
.reg-overview__counts { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1) var(--jf-space-2); margin: 0; padding: 0; list-style: none; }
.reg-overview__deadlines, .reg-note { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.reg-overview__error { color: var(--p-red-600); }
.reg-overview__filter { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1); }
.reg-input { min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-sm); background: var(--jf-color-card); color: var(--jf-color-text); font: inherit; box-sizing: border-box; }
.reg-table { width: 100%; border-collapse: collapse; }
.reg-table th, .reg-table td { padding: var(--jf-space-1) var(--jf-space-1-5); text-align: left; vertical-align: top; border-bottom: 1px solid var(--jf-color-border); }
.reg-table thead th { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.reg-table tbody th { font-weight: var(--jf-weight-semibold); }
.reg-table__actions { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); justify-content: flex-end; }
thead .reg-table__actions { display: table-cell; text-align: right; }
.reg-hints { margin: 0; padding: 0; list-style: none; display: grid; gap: 2px; font-size: var(--jf-text-sm); }
.reg-hints i { margin-right: var(--jf-space-0-5); }
.reg-cancel { display: grid; gap: var(--jf-space-1); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.app-dark .reg-overview__error { color: var(--p-red-300); }
</style>
