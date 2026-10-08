<template>
  <div class="service-report">
    <OverviewHeader title="Anwesenheitsauswertung" subtitle="Teilnahme je Zeitraum, Monatsverlauf und Hinweise auf Handlungsbedarf.">
      <template #actions>
        <Button label="Zum Dienstbuch" icon="pi pi-arrow-left" severity="secondary" outlined @click="router.push({ name: 'servicebook' })" />
      </template>
    </OverviewHeader>

    <div class="report-controls">
      <SegmentedControl v-model="group" label="Personengruppe" :options="groupOptions" />
      <SegmentedControl v-model="range" label="Zeitraum" :options="REPORT_RANGES" />
    </div>

    <StateView v-if="loading && !report" kind="loading" />
    <StateView
      v-else-if="errorKind"
      :kind="errorKind"
      :title="errorKind === 'forbidden' ? 'Keine Berechtigung' : 'Auswertung konnte nicht geladen werden'"
      :message="errorKind === 'forbidden' ? 'Für die Auswertung brauchst du das Recht, Anwesenheiten zu sehen.' : errorMessage"
      @retry="load"
    />

    <template v-else-if="report && current">
      <dl class="report-tiles" :aria-busy="loading || undefined">
        <div class="report-tile">
          <dt>Teilnahmequote</dt>
          <dd class="report-tile__value">{{ formatRate(current.summary.rate) }}</dd>
          <dd class="report-tile__hint">{{ current.summary.recorded }} erfasste Einträge</dd>
        </div>
        <div class="report-tile">
          <dt>Dienste</dt>
          <dd class="report-tile__value">{{ report.services.count }}</dd>
          <dd class="report-tile__hint">{{ formatHours(report.services.hours) }} Dienstzeit</dd>
        </div>
        <div class="report-tile">
          <dt>{{ group === 'members' ? 'Mitglieder' : 'Teammitglieder' }}</dt>
          <dd class="report-tile__value">{{ current.summary.people }}</dd>
          <dd class="report-tile__hint">mit mindestens einem Eintrag</dd>
        </div>
        <div class="report-tile">
          <dt>Mit Hinweis</dt>
          <dd class="report-tile__value">{{ current.summary.with_warnings }}</dd>
          <dd class="report-tile__hint">{{ current.summary.with_warnings ? 'bitte ansprechen' : 'keine Auffälligkeiten' }}</dd>
        </div>
      </dl>

      <section class="report-section" aria-labelledby="report-months">
        <h2 id="report-months" class="report-section__title">Monatsverlauf</h2>
        <AttendanceMonthChart
          :months="current.months"
          label="Teilnahmequote"
          caption="Anteil „anwesend“ an allen erfassten Einträgen des Monats. Monate ohne Einträge sind mit – markiert."
        />
      </section>

      <section class="report-section" aria-labelledby="report-people">
        <div class="report-section__head">
          <h2 id="report-people" class="report-section__title">{{ group === 'members' ? 'Mitglieder' : 'Team' }}</h2>
          <SegmentedControl v-model="show" label="Anzeigen" :options="showOptions" />
        </div>

        <StateView
          v-if="!visiblePeople.length"
          kind="empty"
          :title="show === 'warnings' ? 'Keine Hinweise' : 'Keine Einträge im Zeitraum'"
          :message="show === 'warnings' ? 'Im gewählten Zeitraum fällt niemand auf.' : 'Für diesen Zeitraum wurde noch keine Anwesenheit erfasst.'"
        />

        <ul v-else-if="isMobile" class="people-cards">
          <li v-for="person in visiblePeople" :key="person.id" class="person-card">
            <div class="person-card__top">
              <strong>{{ person.full_name }}</strong>
              <span class="person-card__rate">{{ formatRate(person.rate) }}</span>
            </div>
            <p class="person-card__meta">
              {{ person.present }} anwesend · {{ person.excused }} entschuldigt · {{ person.absent }} fehlt · {{ formatHours(person.hours) }}
            </p>
            <p v-if="person.trend" class="person-card__meta">Trend: {{ trendText(person) }}</p>
            <div v-if="person.warnings.length" class="person-card__warnings">
              <StatusBadge v-for="warning in person.warnings" :key="warning" severity="warning" :label="warningLabel(warning, person)" />
            </div>
          </li>
        </ul>

        <div v-else class="table-wrap">
          <table class="people-table">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col" class="num">Quote</th>
                <th scope="col" class="num">Anwesend</th>
                <th scope="col" class="num">Entschuldigt</th>
                <th scope="col" class="num">Fehlt</th>
                <th scope="col" class="num">Stunden</th>
                <th scope="col">Trend</th>
                <th scope="col">Hinweise</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="person in visiblePeople" :key="person.id">
                <th scope="row">{{ person.full_name }}</th>
                <td class="num strong">{{ formatRate(person.rate) }}</td>
                <td class="num">{{ person.present }}</td>
                <td class="num">{{ person.excused }}</td>
                <td class="num">{{ person.absent }}</td>
                <td class="num">{{ formatHours(person.hours, false) }}</td>
                <td>
                  <span v-if="person.trend" class="trend" :class="trendClass(person)">
                    <i :class="trendIcon(person)" aria-hidden="true"></i>{{ trendText(person) }}
                  </span>
                  <span v-else class="muted" title="Zu wenige Einträge für einen Trend">–</span>
                </td>
                <td>
                  <div class="warnings">
                    <StatusBadge v-for="warning in person.warnings" :key="warning" severity="warning" :label="warningLabel(warning, person)" />
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <p class="report-note">
          Hinweise: geringe Teilnahme unter {{ report.thresholds.low_rate }} % ab {{ report.thresholds.low_rate_min_records }} Einträgen;
          Rückgang um mindestens {{ report.thresholds.decline_points }} Prozentpunkte von der früheren zur späteren Hälfte der eigenen Einträge;
          mindestens {{ report.thresholds.missed_in_a_row }}-mal in Folge nicht anwesend (entschuldigt zählt mit).
          Stunden zählen nur bei Anwesenheit.
        </p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import SegmentedControl, { type SegmentedOption } from '@/components/common/SegmentedControl.vue'
import StateView, { stateForError } from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import AttendanceMonthChart from '@/components/servicebook/molecules/AttendanceMonthChart.vue'
import { servicesApi } from '@/api/servicebook'
import { useMobile } from '@/composables/useMobile'
import { useQueryTableState } from '@/composables/useQueryTableState'
import { classifyApiError, getApiErrorMessage } from '@/utils/apiError'
import { REPORT_RANGES, formatRate, isReportRange, reportPeriod, type ReportRange } from '@/utils/reportPeriod'
import type { AttendanceReport, AttendanceReportPerson, AttendanceWarning } from '@/types/servicebook'

type Group = 'members' | 'staff'
type Show = 'all' | 'warnings'

const URL_DEFAULTS = { group: 'members', range: '12m', show: 'all' }

const router = useRouter()
const { isMobile } = useMobile()
const { getString, syncToUrl } = useQueryTableState()

const group = ref<Group>(getString('group') === 'staff' ? 'staff' : 'members')
const initialRange = getString('range')
const range = ref<ReportRange>(isReportRange(initialRange) ? initialRange : '12m')
const show = ref<Show>(getString('show') === 'warnings' ? 'warnings' : 'all')

const report = ref<AttendanceReport | null>(null)
const loading = ref(false)
const errorKind = ref<'forbidden' | 'offline' | 'error' | null>(null)
const errorMessage = ref('')
let requestId = 0

const current = computed(() => (report.value ? report.value[group.value] : null))
const visiblePeople = computed(() =>
  (current.value?.people ?? []).filter((person) => show.value === 'all' || person.warnings.length > 0)
)

const groupOptions = computed<SegmentedOption<Group>[]>(() => [
  { value: 'members', label: 'Mitglieder', count: report.value?.members.summary.people ?? null },
  { value: 'staff', label: 'Team', count: report.value?.staff.summary.people ?? null }
])
const showOptions = computed<SegmentedOption<Show>[]>(() => [
  { value: 'all', label: 'Alle', count: current.value?.summary.people ?? null },
  { value: 'warnings', label: 'Mit Hinweis', count: current.value?.summary.with_warnings ?? null }
])

async function load() {
  const id = ++requestId
  loading.value = true
  errorKind.value = null
  try {
    const { data } = await servicesApi.getAttendanceReport(reportPeriod(range.value))
    // A later period switch wins over a slower earlier answer.
    if (id === requestId) report.value = data
  } catch (error) {
    if (id !== requestId) return
    report.value = null
    errorKind.value = stateForError(classifyApiError(error))
    errorMessage.value = getApiErrorMessage(error, 'Bitte später erneut versuchen.')
  } finally {
    if (id === requestId) loading.value = false
  }
}

watch(range, load)
watch([group, range, show], () => syncToUrl({ group: group.value, range: range.value, show: show.value }, URL_DEFAULTS))
onMounted(load)

function formatHours(hours: number, withUnit = true): string {
  const value = hours.toLocaleString('de-DE', { maximumFractionDigits: 1 })
  return withUnit ? `${value} Std.` : value
}

function trendText(person: AttendanceReportPerson): string {
  const delta = person.trend?.delta ?? 0
  if (Math.abs(delta) < 10) return 'gleichbleibend'
  const points = Math.round(Math.abs(delta))
  return delta < 0 ? `${points} Punkte weniger` : `${points} Punkte mehr`
}

function trendClass(person: AttendanceReportPerson): string {
  const delta = person.trend?.delta ?? 0
  return delta <= -10 ? 'trend--down' : delta >= 10 ? 'trend--up' : ''
}

function trendIcon(person: AttendanceReportPerson): string {
  const delta = person.trend?.delta ?? 0
  return delta <= -10 ? 'pi pi-arrow-down-right' : delta >= 10 ? 'pi pi-arrow-up-right' : 'pi pi-arrow-right'
}

function warningLabel(warning: AttendanceWarning, person: AttendanceReportPerson): string {
  if (warning === 'low_rate') return 'Geringe Teilnahme'
  if (warning === 'declining') return 'Deutlicher Rückgang'
  return `${person.missed_in_a_row}× in Folge gefehlt`
}
</script>

<style scoped>
.service-report {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-3);
  max-width: 1100px;
  margin: 0 auto;
}

.service-report :deep(.overview-header) {
  margin-bottom: 0;
  padding-bottom: 0;
}

.report-controls {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1-5);
}

.report-tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--jf-space-2);
  margin: 0;
}

.report-tile {
  padding: var(--jf-space-2) var(--jf-space-3);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}

.report-tile dt {
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.report-tile dd {
  margin: 0;
}

.report-tile__value {
  font-size: var(--jf-text-2xl);
  font-weight: var(--jf-weight-bold);
  color: var(--jf-color-text);
}

.report-tile__hint {
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
}

.report-section {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  padding: var(--jf-space-2) var(--jf-space-3);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}

.report-section__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1-5);
}

.report-section__title {
  margin: 0;
  font-size: var(--jf-text-lg);
}

.table-wrap {
  overflow-x: auto;
}

.people-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--jf-text-sm);
}

.people-table th,
.people-table td {
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border-bottom: 1px solid var(--jf-color-border);
  text-align: left;
  vertical-align: middle;
}

.people-table thead th {
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text-muted);
  white-space: nowrap;
}

.people-table tbody th {
  font-weight: var(--jf-weight-medium);
}

.people-table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.people-table .strong {
  font-weight: var(--jf-weight-semibold);
}

.warnings,
.person-card__warnings {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-0-5);
}

.trend {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  white-space: nowrap;
}

.trend--down {
  font-weight: var(--jf-weight-semibold);
}

.muted,
.report-note,
.person-card__meta {
  color: var(--jf-color-text-muted);
}

.report-note {
  margin: 0;
  font-size: var(--jf-text-xs);
}

.people-cards {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.person-card {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
}

.person-card__top {
  display: flex;
  justify-content: space-between;
  gap: var(--jf-space-1);
}

.person-card__rate {
  font-weight: var(--jf-weight-bold);
}

.person-card__meta {
  margin: 0;
  font-size: var(--jf-text-sm);
}
</style>
