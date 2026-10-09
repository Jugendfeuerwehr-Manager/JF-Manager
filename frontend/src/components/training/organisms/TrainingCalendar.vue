<template>
  <div class="training-calendar">
    <!-- Toolbar: period on the left, view switch and actions on the right -->
    <div class="cal-toolbar">
      <div v-if="!showListView" class="cal-period" role="group" aria-label="Monat wählen">
        <Button icon="pi pi-chevron-left" text severity="secondary" aria-label="Vorheriger Monat" @click="prevMonth" />
        <h2 class="cal-title" aria-live="polite">{{ monthLabel }}</h2>
        <Button icon="pi pi-chevron-right" text severity="secondary" aria-label="Nächster Monat" @click="nextMonth" />
        <Button label="Heute" severity="secondary" outlined class="cal-today-button" @click="goToday" />
      </div>
      <h2 v-else class="cal-title">Alle Übungen</h2>

      <div class="cal-actions">
        <SegmentedControl
          :model-value="showListView ? 'list' : 'calendar'"
          :options="viewOptions"
          label="Ansicht"
          @update:model-value="setView"
        />
        <Button icon="pi pi-book" label="Bibliothek" text severity="secondary" @click="router.push('/training/library')" />
        <Button v-if="canCreate" icon="pi pi-bookmark" label="Vorlagen" severity="secondary" outlined @click="openTemplates(null)" />
        <Button v-if="canCreate" icon="pi pi-plus" label="Übung erstellen" @click="openCreate" />
      </div>
    </div>

    <StateView v-if="trainingStore.error" kind="error" :message="trainingStore.error" @retry="loadSessions" />

    <!-- List view -->
    <div v-if="showListView" class="session-list-view">
      <div class="list-search-bar">
        <InputText v-model="listSearch" placeholder="Übungen suchen…" aria-label="Übungen suchen" class="list-search-input" />
      </div>
      <StateView v-if="loading" kind="loading" title="Übungen werden geladen …" />
      <StateView v-else-if="!filteredListSessions.length" kind="empty" title="Keine Übungen gefunden." />
      <div v-else class="session-list-items">
        <div
          v-for="session in filteredListSessions"
          :key="session.occurrence_key"
          class="list-session-item"
          @click="openSession(session)"
        >
          <div class="list-item-date">
            <span class="list-date-day">{{ formatShortDate(session.occurrence_date) }}</span>
            <span class="list-date-time">{{ formatTime(session.start_time) }}</span>
          </div>
          <div class="list-item-info">
            <strong class="session-title-with-icon">
              <i v-if="session.is_recurring" class="pi pi-sync recurrence-icon" title="Terminserie" />
              {{ session.title }} <TrainingStatusBadge :status="session.status" />
            </strong>
            <span v-if="departmentMeta(session.id).label" class="dept-chip" :style="departmentChipStyle(session.id)">
              {{ departmentMeta(session.id).label }}
            </span>
            <span v-if="session.location" class="session-location">{{ session.location }}</span>
          </div>
          <div class="list-item-actions">
            <Button v-if="session.can_manage_plan" icon="pi pi-trash" text severity="danger" :aria-label="`${session.title} löschen`" @click.stop="confirmDeleteSession(session)" />
            <Button icon="pi pi-arrow-right" text :aria-label="`${session.title} öffnen`" @click.stop="openSession(session)" />
          </div>
        </div>
      </div>
    </div>

    <!-- Calendar grid -->
    <div v-if="!showListView && !loading" class="cal-grid" :aria-label="`Übungen im ${monthLabel}`" role="group">
      <!-- Weekday headers -->
      <div
        v-for="(d, index) in weekDays"
        :key="d"
        class="cal-weekday"
        :class="{ 'is-weekend': index >= 5 }"
      >
        <abbr :title="weekDayNames[index]">{{ d }}</abbr>
      </div>

      <!-- Day cells -->
      <div
        v-for="cell in calendarCells"
        :key="cell.key"
        class="cal-cell"
        :class="{
          'other-month': !cell.inMonth,
          'today': cell.isToday,
          'is-weekend': cell.isWeekend,
          'has-sessions': cell.sessions.length > 0,
        }"
        @click="cell.inMonth && openDayDetail(cell)"
      >
        <button
          v-if="cell.inMonth"
          type="button"
          class="cell-day"
          :aria-label="dayLabel(cell)"
          :aria-current="cell.isToday ? 'date' : undefined"
          @click.stop="openDayDetail(cell)"
        >{{ cell.day }}</button>
        <span v-else class="cell-day" aria-hidden="true">{{ cell.day }}</span>
        <div class="cell-sessions">
          <button
            v-for="session in cell.sessions.slice(0, 3)"
            :key="session.occurrence_key"
            type="button"
            class="session-pill"
            :class="`session-pill--${session.status ?? 'draft'}`"
            :style="departmentPillStyle(session.id)"
            :title="sessionLabel(session)"
            :aria-label="sessionLabel(session)"
            @click.stop="openSession(session)"
          >
            <i :class="[trainingStatusMeta(session.status).icon, 'session-pill__status']" aria-hidden="true" />
            <span v-if="session.start_time" class="session-pill__time">{{ formatTime(session.start_time) }}</span>
            <span class="session-pill__title">{{ session.title }}</span>
            <i v-if="session.is_recurring" class="pi pi-sync session-pill__recurring" aria-hidden="true" />
          </button>
          <button
            v-if="cell.sessions.length > 3"
            type="button"
            class="more-pill"
            :aria-label="`${cell.sessions.length - 3} weitere Übungen am ${dayLabel(cell)}`"
            @click.stop="openDayDetail(cell)"
          >
            +{{ cell.sessions.length - 3 }} weitere
          </button>
        </div>
      </div>
    </div>

    <StateView v-else-if="!showListView" kind="loading" title="Kalender wird geladen …" />

    <!-- Create session dialog -->
    <Dialog
      v-model:visible="showCreate"
      header="Übung erstellen"
      :style="{ width: '640px', maxWidth: 'calc(100vw - 24px)' }"
      modal
    >
      <TrainingSessionForm :initial-data="prefillDate ? { date: prefillDate } as any : null" @success="onSessionCreated" @cancel="showCreate = false" />
    </Dialog>

    <TrainingTemplatesDialog v-model:visible="showTemplates" :default-date="templateDate" :department="departmentsStore.activeDepartmentId" @created="(created) => router.push(`/training/sessions/${created.id}/plan`)" />
    <SeriesDialog v-model:visible="showSeries" :session-id="seriesSessionId" @changed="loadSessions" />

    <!-- Day detail panel -->
    <Dialog
      v-model:visible="showDayDetail"
      :header="dayDetailTitle"
      :style="{ width: '500px', maxWidth: 'calc(100vw - 24px)' }"
      modal
    >
      <div class="day-sessions">
        <p v-if="!selectedDaySessions.length" class="day-empty">An diesem Tag ist noch keine Übung geplant.</p>
        <div
          v-for="session in selectedDaySessions"
          :key="session.occurrence_key"
          class="day-session-item"
          @click="openSession(session)"
        >
          <div class="session-time">{{ formatTime(session.start_time) }}</div>
          <div class="session-info">
            <strong class="session-title-with-icon">
              <i v-if="session.is_recurring" class="pi pi-sync recurrence-icon" title="Terminserie" />
              {{ session.title }} <TrainingStatusBadge :status="session.status" />
            </strong>
            <span v-if="departmentMeta(session.id).label" class="dept-chip" :style="departmentChipStyle(session.id)">
              {{ departmentMeta(session.id).label }}
            </span>
            <span v-if="session.location" class="session-location">{{ session.location }}</span>
          </div>
          <div class="session-actions">
            <Button icon="pi pi-calendar" text title="Planer" :aria-label="`${session.title} im Planer öffnen`" @click.stop="goToPlanner(session.id)" />
            <Button v-if="session.can_manage_plan" icon="pi pi-trash" text severity="danger" title="Löschen" :aria-label="`${session.title} löschen`" @click.stop="confirmDeleteSession(session)" />
          </div>
        </div>
      </div>
      <template #footer>
        <Button v-if="canCreate" label="Aus Vorlage" icon="pi pi-bookmark" severity="secondary" outlined @click="openTemplates(selectedCell?.dateStr ?? null)" />
        <Button v-if="canCreate" label="Übung erstellen" icon="pi pi-plus" @click="openCreateForDay" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import TrainingStatusBadge from '../atoms/TrainingStatusBadge.vue'
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import SegmentedControl, { type SegmentedOption } from '@/components/common/SegmentedControl.vue'
import StateView from '@/components/common/StateView.vue'
import TrainingSessionForm from '../molecules/TrainingSessionForm.vue'
import SeriesDialog from '../molecules/SeriesDialog.vue'
import TrainingTemplatesDialog from './TrainingTemplatesDialog.vue'
import { useTrainingStore } from '@/stores/training'
import { useAuthStore } from '@/stores/auth'
import { useDepartmentsStore } from '@/stores/departments'
import {
  calendarSessionsForRange,
  type TrainingCalendarSession,
} from '../utils/recurrence'
import { trainingStatusMeta } from '../utils/trainingStatus'

const router = useRouter()
const confirm = useConfirm()
const trainingStore = useTrainingStore()
const departmentsStore = useDepartmentsStore()
const auth = useAuthStore()
const canCreate = computed(() => auth.hasPerm('training.can_manage_training'))

const today = new Date()
const currentYear = ref(today.getFullYear())
const currentMonth = ref(today.getMonth()) // 0-based

const showCreate = ref(false)
const showDayDetail = ref(false)
const showSeries = ref(false)
const seriesSessionId = ref<number | null>(null)
const showTemplates = ref(false)
const templateDate = ref<string | null>(null)

function openTemplates(date: string | null) {
  templateDate.value = date
  showDayDetail.value = false
  showTemplates.value = true
}
const prefillDate = ref<string | null>(null)
const selectedCell = ref<CalendarCell | null>(null)

// List view state
type CalendarView = 'calendar' | 'list'
const viewOptions: SegmentedOption<CalendarView>[] = [
  { value: 'calendar', label: 'Kalender' },
  { value: 'list', label: 'Liste' },
]
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
    try { await trainingStore.fetchSessions({ limit: 500 }) } catch { /* visible store error */ }
  }
}

function setView(view: CalendarView) {
  if ((view === 'list') !== showListView.value) toggleListView()
}

function formatShortDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('de-DE', {
    weekday: 'short', day: 'numeric', month: 'short',
  })
}

function formatTime(time: string | null | undefined): string {
  return time ? time.slice(0, 5) : ''
}

const weekDays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
const weekDayNames = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']

interface CalendarCell {
  key: string
  day: number
  date: Date
  dateStr: string
  inMonth: boolean
  isToday: boolean
  isWeekend: boolean
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
  calendarSessionsForRange(
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

  // Next month fill: only complete the last week, so a month needs no empty
  // sixth row and fits a notebook screen.
  let next = 1
  while (cells.length % 7 !== 0) {
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
    isWeekend: date.getDay() === 0 || date.getDay() === 6,
    sessions: cellSessions,
  }
}

function dayLabel(cell: CalendarCell): string {
  const date = cell.date.toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long' })
  const count = cell.sessions.length
  const sessionsText = count === 0 ? 'keine Übung' : count === 1 ? '1 Übung' : `${count} Übungen`
  return `${date}${cell.isToday ? ' (heute)' : ''}, ${sessionsText}`
}

function sessionLabel(session: TrainingCalendarSession): string {
  return [
    formatTime(session.start_time),
    session.title,
    trainingStatusMeta(session.status).label,
    session.is_recurring ? 'Terminserie' : '',
    departmentMeta(session.id).label ?? '',
  ].filter(Boolean).join(' · ')
}

async function loadSessions() {
  const from = visibleDateRange.value.fromIso
  const to = visibleDateRange.value.toIso
  try { await trainingStore.fetchSessions({
    date_from: from,
    date_to: to,
    limit: 200,
  }) } catch { /* visible store error, retry button */ }
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
  if (!canCreate.value) return
  prefillDate.value = null
  showCreate.value = true
}

function openCreateForDay() {
  if (!canCreate.value) return
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
  if (session.requires_service_confirmation || !session.linked_service_id || !session.linked_service_start) {
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
  if (!session.can_manage_plan) return
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

async function onSessionCreated(sessionId: number) {
  showCreate.value = false
  // A new recurring exercise only gets further dates through the explicit preview.
  const recurring = !!trainingStore.sessions.find((s) => s.id === sessionId)?.recurrence_rule
  await loadSessions()
  if (recurring) {
    seriesSessionId.value = sessionId
    showSeries.value = true
  }
}

/** Neutral accent for exercises whose department is not loaded. */
const FALLBACK_DEPARTMENT_COLOR = 'var(--p-surface-500)'

function departmentMeta(sessionId: number): { label: string | null; color: string | null } {
  const source = sessions.value.find((s) => s.id === sessionId)
  if (!source || source.department === null) {
    return { label: null, color: null }
  }

  const dept = departmentsStore.departments.find((d) => d.id === source.department)
  if (!dept) {
    return { label: 'Abteilung', color: FALLBACK_DEPARTMENT_COLOR }
  }

  return { label: dept.code || dept.name, color: dept.color || FALLBACK_DEPARTMENT_COLOR }
}

function departmentPillStyle(sessionId: number): Record<string, string> {
  const meta = departmentMeta(sessionId)
  if (!meta.color) return {}
  return { '--session-accent': meta.color }
}

function departmentChipStyle(sessionId: number): Record<string, string> {
  const meta = departmentMeta(sessionId)
  return { '--dept-color': meta.color || FALLBACK_DEPARTMENT_COLOR }
}

watch([currentYear, currentMonth], loadSessions)
onMounted(loadSessions)
</script>

<style scoped>
.training-calendar {
  container: training-calendar / inline-size;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  min-width: 0;
}

/* Toolbar */
.cal-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1-5) var(--jf-space-2);
}

.cal-period {
  display: flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  min-width: 0;
}

.cal-title {
  margin: 0;
  min-width: 9.5rem;
  font-size: var(--jf-text-lg);
  font-weight: var(--jf-weight-bold);
  line-height: var(--jf-leading-tight);
  color: var(--jf-color-text);
  text-align: center;
  white-space: nowrap;
}

.cal-today-button {
  margin-left: var(--jf-space-1);
}

.cal-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: var(--jf-space-1);
}

.cal-period :deep(.p-button),
.cal-actions :deep(.p-button) {
  min-height: var(--jf-touch-target);
}

.cal-period :deep(.p-button-icon-only) {
  min-width: var(--jf-touch-target);
}

/* Month grid */
.cal-grid {
  --cal-cell-min-height: clamp(5.5rem, 11.5vh, 10rem);
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  grid-template-rows: auto;
  grid-auto-rows: minmax(var(--cal-cell-min-height), auto);
  gap: 1px;
  background: var(--jf-color-border);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: var(--jf-shadow-sm);
  overflow: hidden;
}

.cal-weekday {
  padding: var(--jf-space-1) var(--jf-space-1);
  background: var(--jf-color-card);
  color: var(--jf-color-text-muted);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  text-align: left;
}

.cal-weekday abbr {
  text-decoration: none;
}

.cal-cell {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  min-width: 0;
  padding: var(--jf-space-0-5);
  background: var(--jf-color-card);
  cursor: pointer;
  transition: background-color var(--jf-duration);
}

.cal-cell.is-weekend,
.cal-weekday.is-weekend {
  background: color-mix(in srgb, var(--jf-color-ground) 55%, var(--jf-color-card));
}

.cal-cell:not(.other-month):hover {
  background: var(--surface-hover);
}

.cal-cell.other-month {
  background: var(--jf-color-ground);
  cursor: default;
}

.cell-day {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: flex-start;
  flex-shrink: 0;
  min-width: 1.75rem;
  height: 1.75rem;
  padding: 0 var(--jf-space-0-5);
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--jf-color-text);
  font: inherit;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

button.cell-day {
  cursor: pointer;
}

button.cell-day:hover {
  background: var(--jf-color-selected);
  color: var(--jf-color-selected-text);
}

.other-month .cell-day {
  color: var(--jf-color-text-muted);
  font-weight: var(--jf-weight-medium);
}

/* Today: filled day number plus a thin inset ring, not colour alone */
.cal-cell.today {
  box-shadow: inset 0 0 0 2px var(--jf-color-primary);
}

.cal-cell.today .cell-day,
.cal-cell.today button.cell-day:hover {
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
}

.cell-sessions {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

/* Event chips: time + title, truncated; full text in title/aria-label */
.session-pill {
  --session-accent: var(--jf-color-primary);
  display: flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  width: 100%;
  min-width: 0;
  min-height: 1.5rem;
  padding: 1px var(--jf-space-0-5) 1px calc(var(--jf-space-0-5) + 1px);
  border: 1px solid transparent;
  border-left: 3px solid var(--session-accent);
  border-radius: var(--jf-radius-sm);
  background: color-mix(in srgb, var(--jf-color-primary) 9%, var(--jf-color-card));
  color: var(--jf-color-text);
  font: inherit;
  font-size: var(--jf-text-xs);
  line-height: var(--jf-leading-tight);
  text-align: left;
  cursor: pointer;
  transition: background-color var(--jf-duration);
}

.session-pill:hover {
  background: color-mix(in srgb, var(--jf-color-primary) 17%, var(--jf-color-card));
}

.session-pill__status {
  flex-shrink: 0;
  font-size: 0.7rem;
  color: var(--jf-color-text-muted);
}

.session-pill__time {
  flex-shrink: 0;
  color: var(--jf-color-text-muted);
  font-weight: var(--jf-weight-semibold);
  font-variant-numeric: tabular-nums;
}

.session-pill__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-weight: var(--jf-weight-medium);
}

.session-pill__recurring {
  flex-shrink: 0;
  font-size: 0.65rem;
  color: var(--jf-color-text-muted);
}

/* Status: symbol plus shape, never colour alone */
.session-pill--draft {
  border-style: dashed;
  border-color: var(--jf-color-border);
  border-left: 3px solid var(--session-accent);
  background: var(--jf-color-card);
}

.session-pill--completed .session-pill__status {
  color: var(--p-green-700);
}

.session-pill--cancelled {
  background: var(--jf-color-ground);
  color: var(--jf-color-text-muted);
}

.session-pill--cancelled .session-pill__title {
  text-decoration: line-through;
}

.session-pill--cancelled .session-pill__status {
  color: var(--p-red-700);
}

.app-dark .session-pill--completed .session-pill__status { color: var(--p-green-300); }
.app-dark .session-pill--cancelled .session-pill__status { color: var(--p-red-300); }

.more-pill {
  align-self: flex-start;
  min-height: 1.5rem;
  padding: 0 var(--jf-space-0-5);
  border: 0;
  border-radius: var(--jf-radius-sm);
  background: transparent;
  color: var(--jf-color-text-muted);
  font: inherit;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  cursor: pointer;
}

.more-pill:hover {
  color: var(--jf-color-text);
  background: var(--surface-hover);
}

.cell-day:focus-visible,
.session-pill:focus-visible,
.more-pill:focus-visible,
.list-session-item:focus-visible {
  outline: var(--jf-focus-ring);
  outline-offset: 1px;
}

@media (pointer: coarse) {
  .session-pill,
  .more-pill { min-height: 2rem; }
}

/* Large screens: more room per day and slightly larger chips */
@container training-calendar (min-width: 75rem) {
  .cal-cell { padding: var(--jf-space-1); }
  .session-pill { font-size: var(--jf-text-sm); min-height: 1.75rem; }
  .cal-weekday { padding: var(--jf-space-1) var(--jf-space-1-5); }
}

/* Narrow containers (small notebooks with sidebar): drop the time first */
@container training-calendar (max-width: 46rem) {
  .session-pill__time,
  .session-pill__recurring { display: none; }
}

/* Phones: compact cells, chips become thin bars with the title */
@container training-calendar (max-width: 34rem) {
  .cal-grid { --cal-cell-min-height: 4rem; }
  .cal-cell { padding: 2px; gap: 2px; }
  .cal-weekday { padding: var(--jf-space-0-5) 2px; text-align: center; letter-spacing: 0; }
  .cell-day { min-width: 1.5rem; height: 1.5rem; font-size: var(--jf-text-xs); }
  .session-pill { padding: 0 2px; gap: 2px; font-size: 0.65rem; border-left-width: 2px; }
  .session-pill__status { display: none; }
  .more-pill { font-size: 0.65rem; padding: 0 2px; }
}

@container training-calendar (max-width: 40rem) {
  .cal-toolbar { flex-direction: column; align-items: stretch; }
  .cal-period { justify-content: space-between; }
  .cal-title { flex: 1; min-width: 0; font-size: var(--jf-text-md); }
  .cal-today-button { margin-left: 0; }
  .cal-actions { justify-content: flex-start; }
}

/* Department chip */
.dept-chip {
  --dept-color: var(--p-surface-500);
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  width: fit-content;
  padding: 0 var(--jf-space-1);
  border: 1px solid color-mix(in srgb, var(--dept-color) 55%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--dept-color) 12%, transparent);
  color: var(--jf-color-text);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  line-height: 1.5;
}

.dept-chip::before {
  content: '';
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 999px;
  background: var(--dept-color);
}

.session-title-with-icon {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-0-5);
  color: var(--jf-color-text);
}

.recurrence-icon {
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
}

.session-location {
  color: var(--jf-color-text-muted);
  font-size: var(--jf-text-sm);
}

/* Day detail */
.day-sessions {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
}

.day-empty {
  margin: 0;
  color: var(--jf-color-text-muted);
}

.day-session-item {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  cursor: pointer;
  transition: background-color var(--jf-duration);
}

.day-session-item:hover { background: var(--surface-hover); }

.session-time {
  min-width: 2.75rem;
  color: var(--jf-color-text-muted);
  font-size: var(--jf-text-sm);
  font-variant-numeric: tabular-nums;
}

.session-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
}

.session-actions {
  display: flex;
  align-items: center;
}

/* List view */
.session-list-view { display: flex; flex-direction: column; gap: var(--jf-space-2); }
.list-search-bar { display: flex; }
.list-search-input { width: 100%; max-width: 26rem; }

.session-list-items {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  box-shadow: var(--jf-shadow-sm);
  overflow: hidden;
}

.list-session-item {
  display: flex;
  align-items: center;
  gap: var(--jf-space-2);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  cursor: pointer;
  transition: background-color var(--jf-duration);
}

.list-session-item + .list-session-item { border-top: 1px solid var(--jf-color-border); }
.list-session-item:hover { background: var(--surface-hover); }

.list-item-date {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 6.5rem;
}

.list-date-day { font-size: var(--jf-text-sm); font-weight: var(--jf-weight-semibold); color: var(--jf-color-text); }
.list-date-time { font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); font-variant-numeric: tabular-nums; }
.list-item-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: var(--jf-space-0-5); }
.list-item-actions { display: flex; align-items: center; }

@container training-calendar (max-width: 34rem) {
  .list-session-item { flex-wrap: wrap; gap: var(--jf-space-1); padding: var(--jf-space-1-5); }
  .list-item-date { min-width: 0; flex-direction: row; gap: var(--jf-space-1); }
}
</style>
