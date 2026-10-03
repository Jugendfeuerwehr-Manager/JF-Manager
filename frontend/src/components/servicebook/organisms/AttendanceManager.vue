<template>
  <section class="attendance-manager" aria-label="Anwesenheit erfassen">
    <div class="manager-header">
      <div class="tabs" role="group" aria-label="Teilnehmergruppe">
        <Button :outlined="kind !== 'member'" label="Jugendliche" @click="kind = 'member'" />
        <Button
          :outlined="kind !== 'staff'"
          label="Jugendleiter / Ausbilder"
          @click="kind = 'staff'"
        />
        <Button
          text
          label="Team-Auswertung"
          icon="pi pi-chart-bar"
          @click="toggleReport"
        />
      </div>
      <p class="sync-status" role="status">{{ syncMessage }} · Abgleich alle 3 Sekunden</p>
      <InputText v-model="searchQuery" placeholder="Person suchen …" aria-label="Person suchen" />
      <label class="filter"
        ><input v-model="onlyUnmarked" type="checkbox" /> Nur noch nicht erfasst</label
      >
      <p class="legend">
        A = Anwesend · E = Entschuldigt · F = Fehlend. Erneutes Antippen setzt den Status zurück.
      </p>
      <p class="counts">
        {{ counts.present }} anwesend · {{ counts.excused }} entschuldigt ·
        {{ counts.absent }} fehlend · {{ counts.open }} offen
      </p>
    </div>
    <div v-if="showReport" class="report">
      <h3>Jugendleiter und Ausbilder – Auswertung</h3>
      <div class="tabs">
        <label>Von <input v-model="dateFrom" type="date" @change="loadReport" /></label>
        <label>Bis <input v-model="dateTo" type="date" @change="loadReport" /></label>
      </div>
      <p>Erfasste Dienste im Zeitraum, Stunden aus der Dienstdauer bei Anwesenheit.</p>
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
      <p v-if="!report.length">Keine Team-Anwesenheiten im gewählten Zeitraum.</p>
    </div>
    <div v-if="loading" class="empty-state"><ProgressSpinner /></div>
    <div v-else class="members-list">
      <div v-for="person in filteredPeople" :key="`${kind}-${person.id}`" class="member-item">
        <span class="member-name">{{ person.full_name }}</span>
        <AttendanceButtonGroup
          :current-state="person.state"
          :loading="pending.has(`${kind}-${person.id}`)"
          @select="(state) => update(person, state)"
        />
      </div>
      <p v-if="!filteredPeople.length" class="empty-state">
        Keine passenden Personen.
        {{ onlyUnmarked ? 'Alle sichtbaren Anwesenheiten sind erfasst.' : '' }}
      </p>
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
const onlyUnmarked = ref(false)
const pending = ref(new Set<string>())
const loading = ref(true)
const syncMessage = ref('Anwesenheiten werden geladen')
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
      (!onlyUnmarked.value || p.state === null) &&
      p.full_name.toLocaleLowerCase().includes(searchQuery.value.toLocaleLowerCase()),
  ),
)
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
      syncMessage.value = 'Aktueller Stand synchronisiert'
    }
  } catch {
    if (!disposed) syncMessage.value = 'Abgleich unterbrochen – Verbindung wird erneut geprüft'
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
  syncMessage.value = 'Wird gespeichert …'
  try {
    await servicesApi.updateAttendanceBoard(serviceId, {
      kind: selectedKind,
      person_id: person.id,
      state: next,
      expected_state: previous,
    })
    syncMessage.value = 'Gespeichert'
    if (showReport.value) await loadReport()
  } catch (error) {
    person.state = previous
    syncMessage.value = 'Änderung nicht gespeichert'
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
  min-height: 0;
  background: var(--surface-0);
  border-radius: 12px;
  border: 1px solid var(--surface-border);
}
.manager-header,
.report {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
.sync-status,
.legend,
.counts {
  margin: 0;
  font-size: 0.875rem;
}
.sync-status,
.legend {
  color: var(--text-color-secondary);
}
.filter {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.members-list {
  overflow-y: auto;
  padding: 0.5rem 1rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.member-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 0.5rem;
  background: var(--surface-50);
  border-radius: 8px;
}
.member-name {
  font-weight: 500;
  overflow-wrap: anywhere;
}
.empty-state {
  text-align: center;
  padding: 2rem 1rem;
}
.report {
  border-block: 1px solid var(--surface-border);
}
.report h3,
.report p {
  margin: 0;
}
.table-scroll {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  padding: 0.65rem;
  text-align: left;
  border-bottom: 1px solid var(--surface-border);
}
input[type='date'] {
  padding: 0.5rem;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: var(--surface-0);
  color: var(--text-color);
}
</style>
