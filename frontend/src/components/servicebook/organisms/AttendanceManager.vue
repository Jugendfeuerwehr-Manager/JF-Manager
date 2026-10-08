<template>
  <section class="attendance-manager" aria-label="Anwesenheit erfassen">
    <div class="manager-head">
      <div class="manager-head__row">
        <div v-if="!fixedKind" class="kind-switch" role="group" aria-label="Personengruppe">
          <button type="button" :aria-pressed="kind === 'member'" @click="kind = 'member'">Teilnehmende ({{ board.members.length }})</button>
          <button type="button" :aria-pressed="kind === 'staff'" @click="kind = 'staff'">Team ({{ board.staff.length }})</button>
        </div>
        <span v-else class="head-title">{{ kind === 'staff' ? `Betreuende (${board.staff.length})` : `Teilnehmende (${rows.length})` }}</span>
        <span class="save-state" :class="`save-state--${syncState}`" role="status">
          <i :class="syncIcon" aria-hidden="true"></i>{{ syncMessage }}
        </span>
      </div>

      <div class="progress">
        <div class="progress__labels">
          <span><strong>{{ marked }}</strong> von {{ rows.length }} erfasst</span>
          <span class="muted">{{ counts.present }} anwesend · {{ counts.excused }} entschuldigt · {{ counts.absent }} {{ counts.absent === 1 ? 'fehlt' : 'fehlen' }}</span>
        </div>
        <div
          class="progress__track"
          role="progressbar"
          aria-label="Erfasste Anwesenheiten"
          aria-valuemin="0"
          :aria-valuemax="rows.length"
          :aria-valuenow="marked"
          :aria-valuetext="`${marked} von ${rows.length} erfasst`"
        >
          <div class="progress__bar" :style="{ width: `${rows.length ? (marked / rows.length) * 100 : 0}%` }"></div>
        </div>
      </div>

      <div class="manager-head__row">
        <div v-if="!withRegistrations" class="segmented" role="group" aria-label="Anzeige">
          <button type="button" :aria-pressed="filter === 'open'" @click="setFilter('open')">Offen ({{ counts.open }})</button>
          <button type="button" :aria-pressed="filter !== 'open'" @click="setFilter('all')">Alle ({{ rows.length }})</button>
        </div>
        <div v-else class="chips" role="group" aria-label="Anzeige">
          <button v-for="chip in chips" :key="chip.value" type="button" class="chip" :aria-pressed="filter === chip.value" @click="setFilter(chip.value)">
            {{ chip.label }} <strong>{{ chip.count }}</strong>
          </button>
        </div>
        <InputText v-model="searchQuery" placeholder="Person suchen …" aria-label="Person suchen" class="search" />
      </div>
      <button v-if="takeoverCount > 0" type="button" class="takeover" @click="emit('takeover')">
        <i class="pi pi-check-square" aria-hidden="true"></i>{{ takeoverCount }} {{ takeoverCount === 1 ? 'Abmeldung' : 'Abmeldungen' }} als entschuldigt übernehmen
      </button>
    </div>

    <div v-if="loading" class="empty-state"><ProgressSpinner /></div>
    <ul v-else class="people">
      <li v-for="person in filteredPeople" :key="`${kind}-${person.id}`" class="person" :class="{ 'person--suggest': suggestion(person) }">
        <div class="person__identity">
          <span class="person__initials" aria-hidden="true">{{ initials(person.full_name) }}</span>
          <div class="person__text">
            <span class="person__name">{{ person.full_name }}</span>
            <span v-if="person.reg" class="person__registration">
              <RegistrationStatus :person="person.reg" />
              <span v-if="person.reg.conflict" class="person__conflict"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i>Konflikt</span>
            </span>
            <span v-if="person.reg && metaLine(person.reg)" class="person__meta">{{ metaLine(person.reg) }}</span>
          </div>
          <span class="person__state" :class="{ 'person__state--done': person.state }">{{ person.state ? 'erfasst' : 'offen' }}</span>
        </div>
        <AttendanceButtonGroup
          :current-state="person.state"
          :suggest="suggestion(person) ? AttendanceState.EXCUSED : null"
          :person-name="person.full_name"
          :loading="pending.has(`${kind}-${person.id}`)"
          @select="(state) => update(person, state)"
        />
      </li>
      <li v-if="!filteredPeople.length" class="empty-state">
        <template v-if="filter === 'open' && !searchQuery && rows.length">Alle Anwesenheiten sind erfasst.</template>
        <template v-else>Keine passenden Personen.</template>
      </li>
    </ul>
    <p class="hint">Erneutes Antippen des gewählten Status setzt ihn zurück. Änderungen anderer werden alle 3 Sekunden übernommen.</p>

    <router-link
      class="report-link"
      :to="{ name: 'service-report', query: kind === 'staff' ? { group: 'staff' } : {} }"
    >
      <i class="pi pi-chart-bar" aria-hidden="true"></i>Zur Anwesenheitsauswertung
    </router-link>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import AttendanceButtonGroup from '../atoms/AttendanceButtonGroup.vue'
import RegistrationStatus from '../atoms/RegistrationStatus.vue'
import { servicesApi } from '@/api/servicebook'
import { AttendanceState } from '@/types/servicebook'
import type {
  AttendanceBoard,
  AttendanceBoardPerson,
  RegistrationPerson,
  ServiceRegistrations,
} from '@/types/servicebook'
import { formatDateTime, sourceLabel } from '@/utils/registrationState'
import { getApiErrorMessage } from '@/utils/apiError'

const props = defineProps<{
  serviceId: number
  /** Locks the list to one group (service tabs "Anwesenheit" / "Betreuende"). */
  fixedKind?: 'member' | 'staff'
  /** Registrations of the linked planned service (PART-02); enables status, chips, guests and suggestions. */
  registrations?: ServiceRegistrations | null
}>()
const emit = defineEmits<{ takeover: [] }>()

type Filter = 'open' | 'all' | 'cancelled' | 'guests'
interface Row extends AttendanceBoardPerson {
  reg: RegistrationPerson | null
  guest: boolean
}
const toast = useToast()
const board = ref<AttendanceBoard>({ members: [], staff: [] })
const kind = ref<'member' | 'staff'>(props.fixedKind ?? 'member')
const searchQuery = ref('')
const filter = ref<Filter>('open')
/** Attendance set locally for guests that are not on the board yet. */
const guestStates = ref<Record<number, AttendanceState | null>>({})
const pending = ref(new Set<string>())
const loading = ref(true)
const syncMessage = ref('Wird geladen …')
const syncState = ref<'loading' | 'saving' | 'saved' | 'error' | 'offline'>('loading')
const syncIcon = computed(() => ({
  loading: 'pi pi-spin pi-spinner',
  saving: 'pi pi-spin pi-spinner',
  saved: 'pi pi-check',
  error: 'pi pi-exclamation-triangle',
  offline: 'pi pi-wifi',
})[syncState.value])
/** Rows marked while "Offen" is shown stay visible until the filter changes, so a mis-tap can be corrected. */
const keepVisible = ref(new Set<string>())
let timer: ReturnType<typeof setInterval> | undefined
let refreshing = false
let disposed = false
let revision = 0
const withRegistrations = computed(() => kind.value === 'member' && !!props.registrations)
const regById = computed(() => new Map((props.registrations?.people ?? []).map((p) => [p.member_id, p])))
const rows = computed<Row[]>(() => {
  if (kind.value === 'staff') return board.value.staff.map((p) => ({ ...p, reg: null, guest: false }))
  const known = new Set(board.value.members.map((m) => m.id))
  const list: Row[] = board.value.members.map((m) => {
    const reg = regById.value.get(m.id) ?? null
    return { id: m.id, full_name: m.full_name, state: m.state, reg, guest: !!reg && !reg.in_target }
  })
  for (const reg of props.registrations?.people ?? []) {
    if (known.has(reg.member_id) || reg.in_target) continue
    const state = reg.member_id in guestStates.value ? guestStates.value[reg.member_id]! : reg.attendance
    list.push({ id: reg.member_id, full_name: reg.name, state, reg, guest: true })
  }
  return list
})
const isOpen = (p: Row) => p.state === null
const isCancelled = (p: Row) => p.reg?.state === 'cancelled'
function suggestion(p: Row) {
  return kind.value === 'member' && isCancelled(p) && p.state === null
}
const takeoverCount = computed(() => (withRegistrations.value ? rows.value.filter(suggestion).length : 0))
const chips = computed<Array<{ value: Filter; label: string; count: number }>>(() => [
  { value: 'all', label: 'Alle', count: rows.value.length },
  { value: 'open', label: 'Offen', count: rows.value.filter(isOpen).length },
  { value: 'cancelled', label: 'Abgemeldet', count: rows.value.filter(isCancelled).length },
  { value: 'guests', label: 'Gäste', count: rows.value.filter((p) => p.guest).length },
])
const filteredPeople = computed(() =>
  rows.value.filter((p) => {
    const key = `${kind.value}-${p.id}`
    const byFilter =
      filter.value === 'all' ||
      (filter.value === 'open' && (isOpen(p) || keepVisible.value.has(key))) ||
      (filter.value === 'cancelled' && isCancelled(p)) ||
      (filter.value === 'guests' && p.guest)
    return byFilter && p.full_name.toLocaleLowerCase().includes(searchQuery.value.toLocaleLowerCase())
  }),
)
const marked = computed(() => rows.value.filter((p) => p.state !== null).length)
const counts = computed(() => ({
  present: rows.value.filter((p) => p.state === 'A').length,
  excused: rows.value.filter((p) => p.state === 'E').length,
  absent: rows.value.filter((p) => p.state === 'F').length,
  open: rows.value.filter(isOpen).length,
}))

function metaLine(reg: RegistrationPerson) {
  return [sourceLabel(reg.source), formatDateTime(reg.at)].filter(Boolean).join(' · ')
}

async function refresh() {
  if (refreshing || disposed || pending.value.size) return
  refreshing = true
  const serviceId = props.serviceId
  const requestRevision = revision
  try {
    const { data } = await servicesApi.getAttendanceBoard(serviceId)
    // A response started before a local edit must never roll that edit back.
    if (
      !disposed &&
      serviceId === props.serviceId &&
      requestRevision === revision &&
      !pending.value.size
    ) {
      board.value = data
      if (syncState.value !== 'error') {
        syncState.value = 'saved'
        syncMessage.value = 'Gespeichert'
      }
    }
  } catch {
    if (!disposed) {
      syncState.value = 'offline'
      syncMessage.value = 'Offline – Abgleich unterbrochen'
    }
  } finally {
    refreshing = false
    loading.value = false
  }
}

async function update(person: Row, state: AttendanceState) {
  const selectedKind = kind.value
  const key = `${selectedKind}-${person.id}`
  if (pending.value.has(key)) return
  const serviceId = props.serviceId
  const previous = person.state
  const next = previous === state ? null : state
  pending.value.add(key)
  revision++
  setLocalState(person, next)
  if (filter.value === 'open') keepVisible.value.add(key)
  syncState.value = 'saving'
  syncMessage.value = 'Speichert …'
  try {
    await servicesApi.updateAttendanceBoard(serviceId, {
      kind: selectedKind,
      person_id: person.id,
      state: next,
      expected_state: previous,
    })
    syncState.value = 'saved'
    syncMessage.value = 'Gespeichert'
  } catch (error) {
    setLocalState(person, previous)
    syncState.value = 'error'
    syncMessage.value = 'Nicht gespeichert'
    toast.add({
      severity: 'error',
      summary: 'Anwesenheit prüfen',
      detail: getApiErrorMessage(
        error,
        'Speichern fehlgeschlagen. Der aktuelle Stand wird neu geladen.',
      ),
      life: 7000,
    })
  } finally {
    pending.value.delete(key)
    revision++
    await refresh()
  }
}

function setLocalState(person: Row, state: AttendanceState | null) {
  const onBoard = (kind.value === 'staff' ? board.value.staff : board.value.members).find((p) => p.id === person.id)
  if (onBoard) onBoard.state = state
  else guestStates.value = { ...guestStates.value, [person.id]: state }
}

function setFilter(value: Filter) {
  filter.value = value
  keepVisible.value = new Set()
}

async function reload() {
  guestStates.value = {}
  await refresh()
}
defineExpose({ refresh: reload })

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).map((part) => part[0]).slice(0, 2).join('').toUpperCase()
}

function onVisibility() {
  if (!document.hidden) void refresh()
}
onMounted(() => {
  void refresh()
  timer = setInterval(() => {
    if (!document.hidden) void refresh()
  }, 3000)
  document.addEventListener('visibilitychange', onVisibility)
})
watch(() => props.registrations, () => { guestStates.value = {} })
watch(
  () => props.serviceId,
  () => {
    revision++
    board.value = { members: [], staff: [] }
    loading.value = true
    void refresh()
  },
)
onUnmounted(() => {
  disposed = true
  clearInterval(timer)
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<style scoped>
.attendance-manager {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  min-height: 0;
}
.manager-head {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
}
.manager-head__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
}
.kind-switch,
.segmented {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-border);
}
.segmented { flex: 1 1 240px; }
.kind-switch button,
.segmented button {
  flex: 1;
  min-height: 40px;
  padding: 0 var(--jf-space-1-5);
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--jf-color-text-muted);
  font: inherit;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  white-space: nowrap;
  cursor: pointer;
}
.kind-switch button[aria-pressed='true'],
.segmented button[aria-pressed='true'] {
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  box-shadow: 0 1px 2px rgba(23, 32, 51, 0.12);
}
.search { flex: 1 1 200px; }
.head-title { font-weight: var(--jf-weight-bold); font-size: var(--jf-text-md); }
.chips { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); flex: 1 1 100%; }
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 40px;
  padding: 0 var(--jf-space-1-5);
  border: 1px solid var(--p-surface-300);
  border-radius: 999px;
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
  font-size: var(--jf-text-sm);
  cursor: pointer;
}
.chip[aria-pressed='true'] { border-color: var(--jf-color-primary); background: var(--jf-color-selected); color: var(--jf-color-selected-text); font-weight: var(--jf-weight-semibold); }
.takeover {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--jf-space-1);
  min-height: 3rem;
  padding: 0 var(--jf-space-2);
  border: 1px dashed var(--jf-color-primary);
  border-radius: var(--jf-radius-md);
  background: transparent;
  color: var(--jf-color-primary);
  font: inherit;
  font-weight: var(--jf-weight-semibold);
  cursor: pointer;
}
.person--suggest { border-style: dashed; }
.person__text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.person__registration { display: inline-flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1); }
.person__conflict { display: inline-flex; align-items: center; gap: 4px; font-size: var(--jf-text-sm); color: var(--p-amber-900); font-weight: var(--jf-weight-semibold); }
.app-dark .person__conflict { color: var(--p-amber-300); }
.person__meta { display: none; font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }
@media (min-width: 768px) {
  .person__meta { display: block; }
}
.save-state {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  padding: 4px 10px;
  border-radius: 999px;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  background: var(--p-green-100);
  color: var(--p-green-800);
}
.save-state--saving,
.save-state--loading { background: var(--surface-hover); color: var(--jf-color-text-muted); }
.save-state--error,
.save-state--offline { background: var(--p-red-100); color: var(--p-red-800); }
.app-dark .save-state { background: color-mix(in srgb, var(--p-green-400), transparent 84%); color: var(--p-green-300); }
.app-dark .save-state--saving,
.app-dark .save-state--loading { background: var(--surface-hover); color: var(--jf-color-text-muted); }
.app-dark .save-state--error,
.app-dark .save-state--offline { background: color-mix(in srgb, var(--p-red-400), transparent 84%); color: var(--p-red-300); }
.progress { display: flex; flex-direction: column; gap: var(--jf-space-1); }
.progress__labels {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--jf-space-0-5) var(--jf-space-1);
  font-size: var(--jf-text-sm);
}
.progress__track { height: 8px; border-radius: 999px; background: var(--jf-color-border); overflow: hidden; }
.progress__bar { height: 100%; border-radius: 999px; background: var(--p-green-700); transition: width var(--jf-duration); }
.app-dark .progress__bar { background: var(--p-green-400); }
.muted { margin: 0; font-size: 0.8125rem; color: var(--jf-color-text-muted); }
.people {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}
.person {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1) var(--jf-space-2);
  padding: var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}
.person__identity {
  flex: 1 1 220px;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
}
.person__initials {
  flex: none;
  display: inline-grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 999px;
  background: var(--surface-hover);
  font-size: 0.8125rem;
  font-weight: var(--jf-weight-bold);
}
.person__name { min-width: 0; font-weight: var(--jf-weight-semibold); overflow-wrap: anywhere; }
.person__state { font-size: 0.8125rem; color: var(--jf-color-text-muted); }
.person__state--done { color: var(--p-green-800); }
.app-dark .person__state--done { color: var(--p-green-300); }
.person :deep(.attendance-button-group) { flex: 1 1 320px; }
.empty-state { padding: var(--jf-space-4) var(--jf-space-2); text-align: center; color: var(--jf-color-text-muted); }
.hint { margin: 0; font-size: 0.8125rem; color: var(--jf-color-text-muted); }
.report-link {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
  align-self: flex-start;
  min-height: var(--jf-touch-target);
  color: var(--jf-color-primary);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}
.report-link:hover { text-decoration: underline; }
@media (max-width: 767px) {
  .person { padding: var(--jf-space-1-5) var(--jf-space-1); }
  .person :deep(.attendance-button-group) { flex-basis: 100%; }
}
</style>
