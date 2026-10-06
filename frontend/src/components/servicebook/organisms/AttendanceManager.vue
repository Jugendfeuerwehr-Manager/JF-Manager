<template>
  <section class="attendance-manager" aria-label="Anwesenheit erfassen">
    <div class="manager-head">
      <div class="manager-head__row">
        <div class="kind-switch" role="group" aria-label="Personengruppe">
          <button type="button" :aria-pressed="kind === 'member'" @click="kind = 'member'">Teilnehmende ({{ board.members.length }})</button>
          <button type="button" :aria-pressed="kind === 'staff'" @click="kind = 'staff'">Team ({{ board.staff.length }})</button>
        </div>
        <span class="save-state" :class="`save-state--${syncState}`" role="status">
          <i :class="syncIcon" aria-hidden="true"></i>{{ syncMessage }}
        </span>
      </div>

      <div class="progress">
        <div class="progress__labels">
          <span><strong>{{ marked }}</strong> von {{ people.length }} erfasst</span>
          <span class="muted">{{ counts.present }} anwesend · {{ counts.excused }} entschuldigt · {{ counts.absent }} {{ counts.absent === 1 ? 'fehlt' : 'fehlen' }}</span>
        </div>
        <div
          class="progress__track"
          role="progressbar"
          aria-label="Erfasste Anwesenheiten"
          aria-valuemin="0"
          :aria-valuemax="people.length"
          :aria-valuenow="marked"
          :aria-valuetext="`${marked} von ${people.length} erfasst`"
        >
          <div class="progress__bar" :style="{ width: `${people.length ? (marked / people.length) * 100 : 0}%` }"></div>
        </div>
      </div>

      <div class="manager-head__row">
        <div class="segmented" role="group" aria-label="Anzeige">
          <button type="button" :aria-pressed="onlyUnmarked" @click="setOnlyUnmarked(true)">Offen ({{ counts.open }})</button>
          <button type="button" :aria-pressed="!onlyUnmarked" @click="setOnlyUnmarked(false)">Alle ({{ people.length }})</button>
        </div>
        <InputText v-model="searchQuery" placeholder="Person suchen …" aria-label="Person suchen" class="search" />
      </div>
    </div>

    <div v-if="loading" class="empty-state"><ProgressSpinner /></div>
    <ul v-else class="people">
      <li v-for="person in filteredPeople" :key="`${kind}-${person.id}`" class="person">
        <div class="person__identity">
          <span class="person__initials" aria-hidden="true">{{ initials(person.full_name) }}</span>
          <span class="person__name">{{ person.full_name }}</span>
          <span class="person__state" :class="{ 'person__state--done': person.state }">{{ person.state ? 'erfasst' : 'offen' }}</span>
        </div>
        <AttendanceButtonGroup
          :current-state="person.state"
          :person-name="person.full_name"
          :loading="pending.has(`${kind}-${person.id}`)"
          @select="(state) => update(person, state)"
        />
      </li>
      <li v-if="!filteredPeople.length" class="empty-state">
        <template v-if="onlyUnmarked && !searchQuery && people.length">Alle Anwesenheiten sind erfasst.</template>
        <template v-else>Keine passenden Personen.</template>
      </li>
    </ul>
    <p class="hint">Erneutes Antippen des gewählten Status setzt ihn zurück. Änderungen anderer werden alle 3 Sekunden übernommen.</p>

    <div class="report-toggle">
      <Button
        text
        :label="showReport ? 'Team-Auswertung ausblenden' : 'Team-Auswertung'"
        icon="pi pi-chart-bar"
        :aria-expanded="showReport"
        @click="toggleReport"
      />
    </div>
    <div v-if="showReport" class="report">
      <h3>Team – Auswertung</h3>
      <div class="report__range">
        <label>Von <input v-model="dateFrom" type="date" @change="loadReport" /></label>
        <label>Bis <input v-model="dateTo" type="date" @change="loadReport" /></label>
      </div>
      <p class="muted">Erfasste Dienste im Zeitraum, Stunden aus der Dienstdauer bei Anwesenheit.</p>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Anwesend</th>
              <th>Entschuldigt</th>
              <th>Fehlend</th>
              <th>Stunden</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in report" :key="row.id">
              <th>{{ row.full_name }}</th>
              <td>{{ row.present }}</td>
              <td>{{ row.excused }}</td>
              <td>{{ row.absent }}</td>
              <td>{{ row.hours }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!report.length" class="muted">Keine Team-Anwesenheiten im gewählten Zeitraum.</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import AttendanceButtonGroup from '../atoms/AttendanceButtonGroup.vue'
import { servicesApi } from '@/api/servicebook'
import type {
  AttendanceBoard,
  AttendanceBoardPerson,
  AttendanceState,
  StaffAttendanceStatistic,
} from '@/types/servicebook'
import { getApiErrorMessage } from '@/utils/apiError'

const props = defineProps<{ serviceId: number }>()
const toast = useToast()
const board = ref<AttendanceBoard>({ members: [], staff: [] })
const kind = ref<'member' | 'staff'>('member')
const searchQuery = ref('')
const onlyUnmarked = ref(true)
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
const showReport = ref(false)
const report = ref<StaffAttendanceStatistic[]>([])
const dateFrom = ref(`${new Date().getFullYear()}-01-01`)
const dateTo = ref(`${new Date().getFullYear()}-12-31`)
let timer: ReturnType<typeof setInterval> | undefined
let refreshing = false
let disposed = false
let revision = 0
const people = computed(() => (kind.value === 'member' ? board.value.members : board.value.staff))
const filteredPeople = computed(() =>
  people.value.filter(
    (p) =>
      (!onlyUnmarked.value || p.state === null || keepVisible.value.has(`${kind.value}-${p.id}`)) &&
      p.full_name.toLocaleLowerCase().includes(searchQuery.value.toLocaleLowerCase()),
  ),
)
const marked = computed(() => people.value.filter((p) => p.state !== null).length)
const counts = computed(() => ({
  present: people.value.filter((p) => p.state === 'A').length,
  excused: people.value.filter((p) => p.state === 'E').length,
  absent: people.value.filter((p) => p.state === 'F').length,
  open: people.value.filter((p) => p.state === null).length,
}))

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

async function update(person: AttendanceBoardPerson, state: AttendanceState) {
  const selectedKind = kind.value
  const key = `${selectedKind}-${person.id}`
  if (pending.value.has(key)) return
  const serviceId = props.serviceId
  const previous = person.state
  const next = previous === state ? null : state
  pending.value.add(key)
  revision++
  person.state = next
  if (onlyUnmarked.value) keepVisible.value.add(key)
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
    if (showReport.value) await loadReport()
  } catch (error) {
    person.state = previous
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

function setOnlyUnmarked(value: boolean) {
  onlyUnmarked.value = value
  keepVisible.value = new Set()
}

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).map((part) => part[0]).slice(0, 2).join('').toUpperCase()
}

function toggleReport() {
  showReport.value = !showReport.value
  void loadReport()
}

async function loadReport() {
  if (!showReport.value) return
  try {
    report.value = (
      await servicesApi.getStaffStatistics({
        date_from: dateFrom.value || undefined,
        date_to: dateTo.value || undefined,
      })
    ).data.results
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Auswertung',
      detail: getApiErrorMessage(error, 'Auswertung konnte nicht geladen werden.'),
      life: 5000,
    })
  }
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
.person__name { flex: 1; min-width: 0; font-weight: var(--jf-weight-semibold); overflow-wrap: anywhere; }
.person__state { font-size: 0.8125rem; color: var(--jf-color-text-muted); }
.person__state--done { color: var(--p-green-800); }
.app-dark .person__state--done { color: var(--p-green-300); }
.person :deep(.attendance-button-group) { flex: 1 1 320px; }
.empty-state { padding: var(--jf-space-4) var(--jf-space-2); text-align: center; color: var(--jf-color-text-muted); }
.hint { margin: 0; font-size: 0.8125rem; color: var(--jf-color-text-muted); }
.report-toggle { display: flex; }
.report {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}
.report h3 { margin: 0; font-size: var(--jf-text-md); }
.report__range { display: flex; flex-wrap: wrap; gap: var(--jf-space-1-5); font-size: var(--jf-text-sm); }
.report__range label { display: inline-flex; align-items: center; gap: var(--jf-space-1); }
.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: var(--jf-text-sm); }
th, td { padding: 0.65rem; text-align: left; border-bottom: 1px solid var(--jf-color-border); }
input[type='date'] {
  min-height: var(--jf-touch-target);
  padding: 0 0.5rem;
  border: 1px solid var(--p-surface-400);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
}
@media (max-width: 767px) {
  .person { padding: var(--jf-space-1-5) var(--jf-space-1); }
  .person :deep(.attendance-button-group) { flex-basis: 100%; }
}
</style>
