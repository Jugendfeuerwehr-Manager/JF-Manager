<template>
  <div class="dashboard">
    <OverviewHeader :eyebrow="eyebrow" :title="greeting" subtitle="Hier siehst du, was in deinem Bereich ansteht." />

    <section v-if="kpiTiles.length" class="kpi-grid" aria-label="Kennzahlen">
      <router-link v-for="tile in kpiTiles" :key="tile.key" :to="tile.to" class="kpi-tile">
        <span class="kpi-tile__label">{{ tile.label }}<i :class="tile.icon" aria-hidden="true"></i></span>
        <span class="kpi-tile__value" :aria-busy="loading || undefined">{{ loading ? '…' : tile.failed ? '–' : tile.value }}</span>
        <span class="kpi-tile__meta">
          <StatusBadge v-if="tile.failed" label="Nicht geladen" severity="danger" />
          <StatusBadge v-else-if="tile.warning" :label="tile.warning" severity="warning" />
          <span v-else>{{ tile.meta }}</span>
          <span class="kpi-tile__cta">Öffnen<i class="pi pi-arrow-right" aria-hidden="true"></i></span>
        </span>
      </router-link>
    </section>

    <div v-if="failedSources.length" class="dashboard-notice" role="alert">
      <i class="pi pi-exclamation-triangle" aria-hidden="true"></i>
      <span>Einige Kennzahlen konnten nicht geladen werden. Die übrigen Angaben sind aktuell.</span>
      <Button label="Erneut versuchen" icon="pi pi-refresh" severity="secondary" outlined size="small" @click="loadStats" />
    </div>

    <div class="dashboard-columns">
      <section v-if="authStore.canAccessModule('view_service')" class="dashboard-card dashboard-card--wide" aria-labelledby="attendance-title">
        <header class="dashboard-card__header">
          <h2 id="attendance-title">Teilnahme der letzten 12 Monate</h2>
          <router-link to="/servicebook" class="dashboard-link">Dienstbuch<i class="pi pi-arrow-right" aria-hidden="true"></i></router-link>
        </header>

        <StateView v-if="servicebookStore.chartLoading" kind="loading" title="Diagramm wird geladen …" />
        <StateView v-else-if="failedSources.includes('service')" kind="error" message="Die Teilnahmedaten konnten nicht geladen werden." @retry="loadStats" />
        <StateView v-else-if="serviceTrendData.length === 0" kind="empty" title="Noch keine Dienste" message="Für die letzten 12 Monate sind keine Dienste mit Anwesenheit erfasst." />

        <div v-else class="attendance-chart">
          <ul class="attendance-legend" aria-label="Legende">
            <li><span class="legend-swatch legend-swatch--present"></span>A · Anwesend</li>
            <li><span class="legend-swatch legend-swatch--excused"></span>E · Entschuldigt</li>
            <li><span class="legend-swatch legend-swatch--absent"></span>F · Fehlend</li>
          </ul>
          <div ref="chartScroll" class="attendance-scroll">
            <div class="attendance-grid">
              <div
                v-for="service in serviceTrendData"
                :key="service.key"
                class="attendance-column"
                role="img"
                :aria-label="`${service.fullLabel}: ${service.A} anwesend, ${service.E} entschuldigt, ${service.F} fehlend`"
                :title="`${service.fullLabel} · A ${service.A} · E ${service.E} · F ${service.F}`"
              >
                <span class="attendance-total">{{ service.total }}</span>
                <span class="attendance-bar">
                  <span class="attendance-segment attendance-segment--present" :style="{ height: `${(service.A / maxServiceTotal) * 100}%` }"></span>
                  <span class="attendance-segment attendance-segment--excused" :style="{ height: `${(service.E / maxServiceTotal) * 100}%` }"></span>
                  <span class="attendance-segment attendance-segment--absent" :style="{ height: `${(service.F / maxServiceTotal) * 100}%` }"></span>
                </span>
                <span class="attendance-date">{{ service.label }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="dashboard-card" aria-labelledby="shortcuts-title">
        <header class="dashboard-card__header">
          <h2 id="shortcuts-title">Schnellzugriff</h2>
        </header>
        <StateView v-if="visibleModuleTiles.length === 0" kind="forbidden" message="Für dein Konto sind noch keine Module freigegeben." />
        <nav v-else class="shortcut-grid" aria-labelledby="shortcuts-title">
          <router-link v-for="tile in visibleModuleTiles" :key="tile.route" :to="tile.route" class="shortcut">
            <i :class="tile.icon" aria-hidden="true"></i>
            <span>{{ tile.label }}</span>
          </router-link>
        </nav>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import { useAuthStore } from '@/stores/auth'
import { useDepartmentsStore } from '@/stores/departments'
import { useMembersStore } from '@/stores/members'
import { useParentsStore } from '@/stores/parents'
import { useQualificationsStore } from '@/stores/qualifications'
import { useServicebookStore } from '@/stores/servicebook'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

type StatSource = 'member' | 'parent' | 'qualification' | 'service'

interface ModuleTile {
  label: string
  icon: string
  route: string
  viewPerm?: string
}

interface ServiceTrendData {
  key: string
  label: string
  fullLabel: string
  A: number
  E: number
  F: number
  total: number
}

const authStore = useAuthStore()
const departmentsStore = useDepartmentsStore()
const membersStore = useMembersStore()
const parentsStore = useParentsStore()
const qualificationsStore = useQualificationsStore()
const servicebookStore = useServicebookStore()

const loading = ref(true)
const chartScroll = ref<HTMLElement | null>(null)
const failedSources = ref<StatSource[]>([])
const stats = ref({
  totalMembers: 0,
  totalParents: 0,
  totalQualifications: 0,
  expiringQualifications: 0
})

const greeting = computed(() => {
  const hour = new Date().getHours()
  const firstName = authStore.user?.first_name
  const salutation = hour < 11 ? 'Guten Morgen' : hour < 18 ? 'Guten Tag' : 'Guten Abend'
  return firstName ? `${salutation}, ${firstName}` : salutation
})

const eyebrow = computed(() => {
  const today = new Intl.DateTimeFormat('de-DE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())
  const department = departmentsStore.activeDepartment
  return department ? `${today} · ${department.code}` : today
})

const kpiTiles = computed(() => {
  const tiles = []
  if (authStore.canAccessModule('view_member')) {
    tiles.push({ key: 'member', label: 'Mitglieder', icon: 'pi pi-users', to: '/members', value: stats.value.totalMembers, meta: 'im aktuellen Bereich', warning: '', failed: failedSources.value.includes('member') })
  }
  if (authStore.canAccessModule('view_parent')) {
    tiles.push({ key: 'parent', label: 'Eltern', icon: 'pi pi-user', to: '/parents', value: stats.value.totalParents, meta: 'hinterlegte Kontakte', warning: '', failed: failedSources.value.includes('parent') })
  }
  if (authStore.canAccessModule('view_qualification')) {
    const expiring = stats.value.expiringQualifications
    tiles.push({ key: 'qualification', label: 'Qualifikationen', icon: 'pi pi-crown', to: '/qualifications', value: stats.value.totalQualifications, meta: 'keine laufen bald ab', warning: expiring > 0 ? `${expiring} laufen bald ab` : '', failed: failedSources.value.includes('qualification') })
  }
  return tiles
})

const moduleTiles: ModuleTile[] = [
  { label: 'Mitglieder', icon: 'pi pi-users', route: '/members', viewPerm: 'view_member' },
  { label: 'Eltern', icon: 'pi pi-user', route: '/parents', viewPerm: 'view_parent' },
  { label: 'Listen', icon: 'pi pi-list-check', route: '/lists', viewPerm: 'view_memberlist' },
  { label: 'Dienstbuch', icon: 'pi pi-book', route: '/servicebook', viewPerm: 'view_service' },
  { label: 'Ausbildung', icon: 'pi pi-calendar', route: '/training', viewPerm: 'view_trainingsession' },
  { label: 'Qualifikationen', icon: 'pi pi-crown', route: '/qualifications', viewPerm: 'view_qualification' },
  { label: 'Inventar', icon: 'pi pi-box', route: '/inventory', viewPerm: 'view_item' },
  { label: 'Bestellungen', icon: 'pi pi-shopping-cart', route: '/orders', viewPerm: 'view_order' }
]

const visibleModuleTiles = computed(() => {
  return moduleTiles.filter((tile) => !tile.viewPerm || authStore.canAccessModule(tile.viewPerm))
})

const serviceTrendData = computed<ServiceTrendData[]>(() => {
  const chartData = servicebookStore.chartData
  if (!chartData) return []

  const now = new Date()
  const lastYearDate = new Date(now)
  lastYearDate.setFullYear(now.getFullYear() - 1)

  const labelFormatter = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit' })
  const fullLabelFormatter = new Intl.DateTimeFormat('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })

  const services: ServiceTrendData[] = []

  chartData.service_dates.forEach((dateString, index) => {
    const date = new Date(`${dateString}T00:00:00`)
    if (Number.isNaN(date.getTime()) || date < lastYearDate || date > now) {
      return
    }

    const A = chartData.attendance_data.A[index] || 0
    const E = chartData.attendance_data.E[index] || 0
    const F = chartData.attendance_data.F[index] || 0

    services.push({
      key: `${dateString}-${index}`,
      label: labelFormatter.format(date),
      fullLabel: fullLabelFormatter.format(date),
      A,
      E,
      F,
      total: A + E + F
    })
  })

  return services
})

const maxServiceTotal = computed(() => {
  const totals = serviceTrendData.value.map((service) => service.total)
  const max = Math.max(...totals, 0)
  return max === 0 ? 1 : max
})

async function loadStats() {
  loading.value = true
  const requests: [StatSource, () => Promise<unknown>][] = []
  if (authStore.canAccessModule('view_member')) requests.push(['member', () => membersStore.fetchMembers()])
  if (authStore.canAccessModule('view_parent')) requests.push(['parent', () => parentsStore.fetchParents()])
  if (authStore.canAccessModule('view_qualification')) requests.push(['qualification', () => qualificationsStore.fetchStatistics()])
  if (authStore.canAccessModule('view_service')) requests.push(['service', () => servicebookStore.fetchChartData()])

  const results = await Promise.allSettled(requests.map(([, request]) => request()))
  failedSources.value = requests.filter((_, index) => results[index]!.status === 'rejected').map(([source]) => source)

  stats.value = {
    totalMembers: membersStore.pagination.count,
    totalParents: parentsStore.pagination.count,
    totalQualifications: qualificationsStore.statistics?.total_qualifications || 0,
    expiringQualifications: qualificationsStore.statistics?.expiring_qualifications || 0
  }
  loading.value = false
  // Most recent services first in view on narrow screens
  await nextTick()
  if (chartScroll.value) chartScroll.value.scrollLeft = chartScroll.value.scrollWidth
}

onMounted(loadStats)
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-3);
}

.dashboard :deep(.overview-header) {
  margin-bottom: 0;
  padding-bottom: 0;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--jf-space-2);
}

.kpi-tile {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  padding: var(--jf-space-2) var(--jf-space-3);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: var(--jf-shadow-sm);
  color: var(--jf-color-text);
  text-decoration: none;
  transition: box-shadow var(--jf-duration), border-color var(--jf-duration);
}

.kpi-tile:hover {
  border-color: var(--p-surface-300);
  box-shadow: var(--jf-shadow-md);
}

.kpi-tile__label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--jf-color-text-muted);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-medium);
}

.kpi-tile__value {
  font-size: 2rem;
  font-weight: var(--jf-weight-bold);
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.kpi-tile__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
  min-height: 24px;
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.kpi-tile__cta {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  color: var(--jf-color-primary);
  font-weight: var(--jf-weight-semibold);
}

.kpi-tile__cta i,
.dashboard-link i {
  font-size: 0.75rem;
}

.dashboard-notice {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1) var(--jf-space-2);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border: 1px solid var(--p-red-200);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-selected);
  color: var(--jf-color-selected-text);
  font-size: var(--jf-text-sm);
}

.dashboard-notice span {
  flex: 1 1 240px;
}

.dashboard-columns {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-3);
  align-items: flex-start;
}

.dashboard-card {
  flex: 1 1 300px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  padding: var(--jf-space-3);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: var(--jf-shadow-sm);
}

.dashboard-card--wide {
  flex: 3 1 480px;
}

.dashboard-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-2);
}

.dashboard-card__header h2 {
  margin: 0;
  font-size: var(--jf-text-lg);
  font-weight: var(--jf-weight-semibold);
}

.dashboard-link {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  min-height: var(--jf-touch-target);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-primary);
  text-decoration: none;
}

.attendance-chart {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.attendance-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1) var(--jf-space-2);
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.attendance-legend li {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
}

.legend-swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.legend-swatch--present,
.attendance-segment--present {
  background: var(--p-green-600);
}

.legend-swatch--excused,
.attendance-segment--excused {
  background: var(--p-amber-400);
}

.legend-swatch--absent,
.attendance-segment--absent {
  background: var(--p-red-700);
}

.attendance-scroll {
  overflow-x: auto;
  padding-bottom: var(--jf-space-0-5);
}

.attendance-grid {
  display: flex;
  align-items: flex-end;
  gap: var(--jf-space-1);
  min-height: 220px;
}

.attendance-column {
  display: flex;
  flex: 1 0 28px;
  flex-direction: column;
  align-items: center;
  gap: var(--jf-space-0-5);
  min-width: 28px;
}

.attendance-total {
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text-muted);
}

.attendance-bar {
  display: flex;
  flex-direction: column-reverse;
  width: 100%;
  max-width: 28px;
  height: 160px;
  border-radius: var(--jf-radius-sm);
  overflow: hidden;
  background: var(--surface-hover);
}

.attendance-segment {
  display: block;
  width: 100%;
}

.attendance-date {
  font-size: 0.6875rem;
  color: var(--jf-color-text-muted);
  white-space: nowrap;
}

.shortcut-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: var(--jf-space-1);
}

.shortcut {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  min-height: 52px;
  padding: 0 var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  color: var(--jf-color-text);
  text-decoration: none;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-medium);
  transition: background-color var(--jf-duration);
}

.shortcut i {
  color: var(--jf-color-primary);
}

.shortcut:hover {
  background: var(--surface-hover);
}

@media (max-width: 767px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--jf-space-1-5);
  }

  .kpi-tile {
    padding: var(--jf-space-1-5) var(--jf-space-2);
  }

  .kpi-tile:last-child:nth-child(odd) {
    grid-column: 1 / -1;
  }

  .kpi-tile__value {
    font-size: 1.5rem;
  }

  .kpi-tile__cta {
    display: none;
  }

  .dashboard-card {
    padding: var(--jf-space-2);
  }
}
</style>
