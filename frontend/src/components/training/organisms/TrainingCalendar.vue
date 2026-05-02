<template>
  <div class="training-calendar">
    <!-- Calendar nav bar -->
    <div class="cal-nav">
      <!-- Row 1: month navigation -->
      <div class="cal-nav-row cal-nav-month">
        <Button icon="pi pi-chevron-left" text @click="prevMonth" />
        <h2 class="cal-title">{{ monthLabel }}</h2>
        <Button icon="pi pi-chevron-right" text @click="nextMonth" />
      </div>

      <!-- Row 2: action buttons (wrap on mobile) -->
      <div class="cal-nav-row cal-nav-actions">
        <Button
          :icon="showListView ? 'pi pi-calendar' : 'pi pi-list'"
          :label="showListView ? 'Kalender' : 'Liste'"
          size="small"
          severity="secondary"
          outlined
          @click="toggleListView"
        />
        <Button icon="pi pi-book" label="Bibliothek" size="small" severity="secondary" outlined @click="router.push('/training/library')" />
        <Button label="Heute" size="small" outlined @click="goToday" />
        <Button icon="pi pi-plus" label="Übung erstellen" size="small" @click="openCreate" />
      </div>
    </div>

    <!-- List view -->
    <div v-if="showListView" class="session-list-view">
      <div class="list-search-bar">
        <InputText v-model="listSearch" placeholder="Übungen suchen…" class="list-search-input" />
      </div>
      <div v-if="loading" class="loading-state"><ProgressSpinner /></div>
      <div v-else-if="!filteredListSessions.length" class="empty-state">
        <i class="pi pi-calendar text-4xl mb-2" /><p>Keine Übungen gefunden.</p>
      </div>
      <div v-else class="session-list-items">
        <div
          v-for="session in filteredListSessions"
          :key="session.occurrence_key"
          class="list-session-item"
          @click="openSession(session)"
        >
          <div class="list-item-date">
            <span class="list-date-day">{{ formatShortDate(session.occurrence_date) }}</span>
            <span class="list-date-time">{{ session.start_time ?? '' }}</span>
          </div>
          <div class="list-item-info">
            <strong class="session-title-with-icon">
              <i v-if="session.is_recurring" class="pi pi-sync recurrence-icon" title="Terminserie" />
              {{ session.title }}
            </strong>
            <span v-if="departmentMeta(session.id).label" class="dept-chip" :style="departmentChipStyle(session.id)">
              {{ departmentMeta(session.id).label }}
            </span>
            <span v-if="session.location" class="text-color-secondary text-sm">{{ session.location }}</span>
          </div>
          <div class="list-item-actions">
            <Button icon="pi pi-trash" text size="small" severity="danger" @click.stop="confirmDeleteSession(session)" />
            <Button icon="pi pi-arrow-right" text size="small" @click.stop="openSession(session)" />
          </div>
        </div>
      </div>
    </div>

    <!-- Calendar grid -->
    <div v-if="!showListView && !loading" class="cal-grid">
      <!-- Weekday headers -->
      <div v-for="d in weekDays" :key="d" class="cal-weekday">{{ d }}</div>

      <!-- Day cells -->
      <div
        v-for="cell in calendarCells"
        :key="cell.key"
        class="cal-cell"
        :class="{
          'other-month': !cell.inMonth,
          'today': cell.isToday,
          'has-sessions': cell.sessions.length > 0,
        }"
        @click="cell.inMonth && openDayDetail(cell)"
      >
        <span class="cell-day">{{ cell.day }}</span>
        <div class="cell-sessions">
          <div
            v-for="session in cell.sessions.slice(0, 3)"
            :key="session.occurrence_key"
            class="session-pill"
            :style="departmentPillStyle(session.id)"
            :title="session.title"
            @click.stop="openSession(session)"
          >
            <i v-if="session.is_recurring" class="pi pi-sync recurrence-icon" />
            {{ session.title }}
          </div>
          <div v-if="cell.sessions.length > 3" class="more-pill">
            +{{ cell.sessions.length - 3 }} weitere
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!showListView" class="loading-state">
      <ProgressSpinner />
    </div>

    <!-- Create session dialog -->
    <Dialog
      v-model:visible="showCreate"
      header="Übung erstellen"
      :style="{ width: '640px' }"
      modal
    >
      <TrainingSessionForm :initial-data="prefillDate ? { date: prefillDate } as any : null" @success="onSessionCreated" @cancel="showCreate = false" />
    </Dialog>

    <!-- Day detail panel -->
    <Dialog
      v-model:visible="showDayDetail"
      :header="dayDetailTitle"
      :style="{ width: '500px' }"
      modal
    >
      <div class="day-sessions">
        <div
          v-for="session in selectedDaySessions"
          :key="session.occurrence_key"
          class="day-session-item"
          @click="openSession(session)"
        >
          <div class="session-time">{{ session.start_time ?? '' }}</div>
          <div class="session-info">
            <strong class="session-title-with-icon">
              <i v-if="session.is_recurring" class="pi pi-sync recurrence-icon" title="Terminserie" />
              {{ session.title }}
            </strong>
            <span v-if="departmentMeta(session.id).label" class="dept-chip" :style="departmentChipStyle(session.id)">
              {{ departmentMeta(session.id).label }}
            </span>
            <span v-if="session.location" class="text-color-secondary text-sm">{{ session.location }}</span>
          </div>
          <div class="session-actions">
            <Button icon="pi pi-calendar" text size="small" title="Planer" @click.stop="goToPlanner(session.id)" />
            <Button icon="pi pi-trash" text size="small" severity="danger" title="Löschen" @click.stop="confirmDeleteSession(session)" />
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="Übung erstellen" icon="pi pi-plus" size="small" @click="openCreateForDay" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import TrainingSessionForm from '../molecules/TrainingSessionForm.vue'
import { useTrainingStore } from '@/stores/training'
import { useDepartmentsStore } from '@/stores/departments'
import {
  expandTrainingSessionsForRange,
  type TrainingCalendarSession,
} from '../utils/recurrence'

const router = useRouter()
const confirm = useConfirm()
const trainingStore = useTrainingStore()
const departmentsStore = useDepartmentsStore()

const today = new Date()
const currentYear = ref(today.getFullYear())
const currentMonth = ref(today.getMonth()) // 0-based

const showCreate = ref(false)
const showDayDetail = ref(false)
const prefillDate = ref<string | null>(null)
const selectedCell = ref<CalendarCell | null>(null)

// List view state
const showListView = ref(false)
const listSearch = ref('')

const filteredListSessions = computed(() => {
  const q = listSearch.value.toLowerCase().trim()
  if (!q) return displaySessions.value
  return displaySessions.value.filter(
    (s) => s.title.toLowerCase().includes(q) || s.location?.toLowerCase().includes(q),
  )
})

async function toggleListView() {
  showListView.value = !showListView.value
  if (showListView.value) {
    // Load all upcoming sessions for list mode
    await trainingStore.fetchSessions({ limit: 500 })
  }
}

function formatShortDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('de-DE', {
    weekday: 'short', day: 'numeric', month: 'short',
  })
}

const weekDays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']

interface CalendarCell {
  key: string
  day: number
  date: Date
  dateStr: string
  inMonth: boolean
  isToday: boolean
  sessions: TrainingCalendarSession[]
}

const loading = computed(() => trainingStore.loading)
const sessions = computed(() => trainingStore.sessions)

const visibleDateRange = computed(() => {
  const from = new Date(currentYear.value, currentMonth.value - 1, 1)
  const to = new Date(currentYear.value, currentMonth.value + 2, 0)
  return {
    from,
    to,
    fromIso: toIsoDate(from),
    toIso: toIsoDate(to),
  }
})

const displaySessions = computed(() =>
  expandTrainingSessionsForRange(
    sessions.value,
    visibleDateRange.value.fromIso,
    visibleDateRange.value.toIso,
  ),
)

const monthLabel = computed(() => {
  return new Date(currentYear.value, currentMonth.value, 1).toLocaleDateString('de-DE', {
    month: 'long',
    year: 'numeric',
  })
})

const dayDetailTitle = computed(() => {
  if (!selectedCell.value) return ''
  return selectedCell.value.date.toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long' })
})

const selectedDaySessions = computed(() => selectedCell.value?.sessions ?? [])

const calendarCells = computed<CalendarCell[]>(() => {
  const year = currentYear.value
  const month = currentMonth.value
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)

  // Monday-based (0=Mo … 6=So)
  let startDow = firstDay.getDay() - 1
  if (startDow < 0) startDow = 6

  const cells: CalendarCell[] = []

  // Previous month fill
  for (let i = startDow - 1; i >= 0; i--) {
    const d = new Date(year, month, -i)
    cells.push(makeCell(d, false))
  }

  // Current month
  for (let d = 1; d <= lastDay.getDate(); d++) {
    cells.push(makeCell(new Date(year, month, d), true))
  }

  // Next month fill to complete 6 rows (42 cells)
  let next = 1
  while (cells.length < 42) {
    cells.push(makeCell(new Date(year, month + 1, next++), false))
  }

  return cells
})

function makeCell(date: Date, inMonth: boolean): CalendarCell {
  const dateStr = toIsoDate(date)
  const isToday =
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate()

  const cellSessions = displaySessions.value.filter((s) => s.occurrence_date === dateStr)

  return {
    key: dateStr,
    day: date.getDate(),
    date,
    dateStr,
    inMonth,
    isToday,
    sessions: cellSessions,
  }
}

async function loadSessions() {
  const from = visibleDateRange.value.fromIso
  const to = visibleDateRange.value.toIso
  await trainingStore.fetchSessions({
    date_from: from,
    date_to: to,
    limit: 200,
  })
}

function toIsoDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function prevMonth() {
  if (currentMonth.value === 0) { currentYear.value--; currentMonth.value = 11 }
  else currentMonth.value--
}
function nextMonth() {
  if (currentMonth.value === 11) { currentYear.value++; currentMonth.value = 0 }
  else currentMonth.value++
}
function goToday() {
  currentYear.value = today.getFullYear()
  currentMonth.value = today.getMonth()
}

function openCreate() {
  prefillDate.value = null
  showCreate.value = true
}

function openCreateForDay() {
  if (selectedCell.value) prefillDate.value = selectedCell.value.dateStr
  showDayDetail.value = false
  showCreate.value = true
}

function openDayDetail(cell: CalendarCell) {
  selectedCell.value = cell
  showDayDetail.value = true
}

function openSession(session: TrainingCalendarSession) {
  router.push(`/training/sessions/${session.id}/plan`)
}

function hasFutureLinkedService(session: TrainingCalendarSession): boolean {
  if (!session.linked_service_id || !session.linked_service_start) {
    return false
  }
  return new Date(session.linked_service_start) >= new Date()
}

async function runDeleteSession(
  session: TrainingCalendarSession,
  deleteLinkedService: boolean,
) {
  await trainingStore.deleteSession(session.id, { deleteLinkedService })
  if (selectedCell.value) {
    selectedCell.value = calendarCells.value.find((c) => c.key === selectedCell.value?.key) ?? null
  }
  await loadSessions()
}

function confirmDeleteSession(session: TrainingCalendarSession) {
  if (hasFutureLinkedService(session)) {
    confirm.require({
      header: 'Verknüpften Dienst löschen?',
      message:
        'Dieser zukünftige Termin ist mit einem Dienstbuch-Eintrag verknüpft. Mit "Mit Dienstbuch löschen" werden beide Einträge gelöscht. Mit "Nur Übung löschen" bleibt der Dienstbuch-Eintrag erhalten und wird nur entkoppelt.',
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: 'Mit Dienstbuch löschen',
      rejectLabel: 'Nur Übung löschen',
      acceptClass: 'p-button-danger',
      accept: () => runDeleteSession(session, true),
      reject: () => runDeleteSession(session, false),
    })
    return
  }

  confirm.require({
    header: 'Übung löschen?',
    message: 'Soll diese Übung wirklich gelöscht werden?',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: () => runDeleteSession(session, false),
  })
}

function goToPlanner(sessionId: number) {
  showDayDetail.value = false
  router.push(`/training/sessions/${sessionId}/plan`)
}

function onSessionCreated(_sessionId: number) {
  showCreate.value = false
  loadSessions()
}

function departmentMeta(sessionId: number): { label: string | null; color: string | null } {
  const source = sessions.value.find((s) => s.id === sessionId)
  if (!source || source.department === null) {
    return { label: null, color: null }
  }

  const dept = departmentsStore.departments.find((d) => d.id === source.department)
  if (!dept) {
    return { label: 'Abteilung', color: '#64748B' }
  }

  return { label: dept.code || dept.name, color: dept.color || '#64748B' }
}

function departmentPillStyle(sessionId: number): Record<string, string> {
  const meta = departmentMeta(sessionId)
  if (!meta.color) return {}
  return { borderLeft: `4px solid ${meta.color}` }
}

function departmentChipStyle(sessionId: number): Record<string, string> {
  const meta = departmentMeta(sessionId)
  const color = meta.color || '#64748B'
  return {
    borderColor: color,
    color,
    backgroundColor: `${color}1A`,
  }
}

watch([currentYear, currentMonth], loadSessions)
onMounted(loadSessions)
</script>

<style scoped>
.training-calendar { display: flex; flex-direction: column; gap: 1rem; }

.dept-chip {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border: 1px solid;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.1rem 0.45rem;
}

.cal-nav {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.cal-nav-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.cal-nav-month {
  /* Month row: chevrons + title, centered */
}

.cal-nav-actions {
  flex-wrap: wrap;
}

.cal-title { font-size: 1.25rem; font-weight: 600; margin: 0; min-width: 160px; text-align: center; }
.spacer { flex: 1; }

/* Compact icon-only buttons on very small screens */
@media (max-width: 480px) {
  .cal-title { font-size: 1rem; min-width: 130px; }
}

.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  background: var(--surface-border);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  overflow: hidden;
}

.cal-weekday {
  background: var(--surface-50);
  text-align: center;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  padding: 0.5rem;
}

.cal-cell {
  background: var(--surface-card);
  min-height: 90px;
  padding: 0.375rem;
  cursor: pointer;
  transition: background 0.1s;
}
@media (max-width: 640px) {
  .cal-cell { min-height: 60px; padding: 0.25rem; }
  .session-pill { font-size: 0.65rem; padding: 1px 3px; }
}
.cal-cell:hover { background: var(--surface-hover); }
.cal-cell.other-month { background: var(--surface-50); opacity: 0.6; cursor: default; }
.cal-cell.today .cell-day {
  background: var(--primary-color);
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cell-day {
  font-size: 0.85rem;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin-bottom: 0.25rem;
}

.cell-sessions { display: flex; flex-direction: column; gap: 2px; }

.session-pill {
  background: var(--primary-100, #dbeafe);
  color: var(--primary-700, #1d4ed8);
  font-size: 0.725rem;
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
}
.session-pill:hover { background: var(--primary-200, #bfdbfe); }

.session-title-with-icon {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.recurrence-icon {
  font-size: 0.7rem;
  opacity: 0.9;
}

.more-pill {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
  padding: 0 5px;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.day-sessions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.day-session-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: background 0.1s;
}
.day-session-item:hover { background: var(--surface-hover); }
.session-time { font-size: 0.85rem; color: var(--text-color-secondary); min-width: 40px; }
.session-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }

/* List view */
.session-list-view { display: flex; flex-direction: column; gap: 1rem; }
.list-search-bar { display: flex; }
.list-search-input { width: 100%; max-width: 420px; }

.session-list-items { display: flex; flex-direction: column; gap: 0.5rem; }
.list-session-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-card);
  cursor: pointer;
  transition: background 0.1s;
}
.list-session-item:hover { background: var(--surface-hover); }
.list-item-date {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 100px;
}
.list-date-day { font-size: 0.875rem; font-weight: 600; }
.list-date-time { font-size: 0.8rem; color: var(--text-color-secondary); }
.list-item-info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.list-item-actions { display: flex; align-items: center; gap: 0.25rem; }
.empty-state { text-align: center; color: var(--text-color-secondary); padding: 2rem; }
</style>
