<template>
  <div class="dashboard">
    <div class="mb-4">
      <h1 class="text-4xl font-bold mb-2">Übersicht</h1>
      <p class="text-surface-600">Willkommen zurück, {{ authStore.userFullName }}</p>
    </div>

    <div class="grid">
      <div class="col-4 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Mitglieder</div>
                <div class="text-3xl font-bold">{{ stats.totalMembers }}</div>
              </div>
              <i class="pi pi-users text-4xl text-primary"></i>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-4 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Eltern</div>
                <div class="text-3xl font-bold">{{ stats.totalParents }}</div>
              </div>
              <i class="pi pi-user text-4xl text-blue-500"></i>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-4 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Qualifikationen</div>
                <div class="text-3xl font-bold">{{ stats.totalQualifications }}</div>
                <div v-if="stats.expiringQualifications > 0" class="text-xs text-orange-500 mt-1">
                  {{ stats.expiringQualifications }} laufen bald ab
                </div>
              </div>
              <i class="pi pi-certificate text-4xl text-purple-500"></i>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-4 md:col-6 lg:col-3">
        <Card>
          <template #content>
            <div class="flex items-center justify-between">
              <div>
                <div class="text-surface-500 text-sm mb-1">Inventar</div>
                <div class="text-3xl font-bold">-</div>
              </div>
              <i class="pi pi-box text-4xl text-orange-500"></i>
            </div>
          </template>
        </Card>
      </div>
    </div>

    <div class="grid mt-4">
      <div class="col-12">
        <Card>
          <template #title>Anwesenheit A/E/F (Letzte 12 Monate)</template>
          <template #content>
            <div v-if="servicebookStore.chartLoading" class="text-center text-surface-500 py-4">
              <i class="pi pi-spin pi-spinner text-2xl"></i>
              <p class="mt-2 mb-0">Diagramm wird geladen...</p>
            </div>

            <div v-else-if="serviceTrendData.length === 0" class="text-center text-surface-500 py-4">
              <i class="pi pi-chart-bar text-3xl mb-2"></i>
              <p>Keine Dienstbuch-Daten für die letzten 12 Monate vorhanden.</p>
            </div>

            <div v-else class="attendance-chart-wrapper">
              <div class="attendance-legend">
                <span class="legend-item">
                  <span class="legend-color legend-color--present"></span>
                  A - Anwesend
                </span>
                <span class="legend-item">
                  <span class="legend-color legend-color--excused"></span>
                  E - Entschuldigt
                </span>
                <span class="legend-item">
                  <span class="legend-color legend-color--absent"></span>
                  F - Fehlend
                </span>
              </div>

              <div class="attendance-chart-scroll">
                <div class="attendance-chart-grid">
                  <div
                    v-for="service in serviceTrendData"
                    :key="service.key"
                    class="attendance-column"
                    :title="`${service.fullLabel} | A:${service.A} E:${service.E} F:${service.F}`"
                  >
                    <div class="attendance-total">{{ service.total }}</div>
                    <div class="attendance-bar">
                      <div
                        class="attendance-segment attendance-segment--present"
                        :style="{ height: `${(service.A / maxServiceTotal) * 100}%` }"
                      ></div>
                      
                      <div
                        class="attendance-segment attendance-segment--excused"
                        :style="{ height: `${(service.E / maxServiceTotal) * 100}%` }"
                      ></div>
                      <div
                        class="attendance-segment attendance-segment--absent"
                        :style="{ height: `${(service.F / maxServiceTotal) * 100}%` }"
                      ></div>
                    </div>
                    <div class="attendance-month">{{ service.label }}</div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </Card>
      </div>
    </div>

    <div class="grid mt-4">
      <div class="col-12">
        <Card>
          <template #title>Schnellzugriff Apps</template>
          <template #content>
            <div v-if="visibleModuleTiles.length === 0" class="text-center text-surface-500 py-4">
              <i class="pi pi-lock text-3xl mb-2"></i>
              <p>Keine freigegebenen Module in der aktuellen Berechtigungskonfiguration.</p>
            </div>

            <div v-else class="module-grid">
              <button
                v-for="tile in visibleModuleTiles"
                :key="tile.route"
                type="button"
                class="module-tile"
                @click="router.push(tile.route)"
              >
                <i :class="['module-icon', tile.icon]" aria-hidden="true"></i>
                <span class="module-label">{{ tile.label }}</span>
              </button>
            </div>
          </template>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useMembersStore } from '@/stores/members'
import { useParentsStore } from '@/stores/parents'
import { useQualificationsStore } from '@/stores/qualifications'
import { useServicebookStore } from '@/stores/servicebook'
import Card from 'primevue/card'

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

const router = useRouter()
const authStore = useAuthStore()
const membersStore = useMembersStore()
const parentsStore = useParentsStore()
const qualificationsStore = useQualificationsStore()
const servicebookStore = useServicebookStore()

const stats = ref({
  totalMembers: 0,
  totalParents: 0,
  totalQualifications: 0,
  expiringQualifications: 0
})

const moduleTiles: ModuleTile[] = [
  { label: 'Mitglieder', icon: 'pi pi-users', route: '/members', viewPerm: 'view_member' },
  { label: 'Eltern', icon: 'pi pi-user', route: '/parents', viewPerm: 'view_parent' },
  { label: 'Dienstbuch', icon: 'pi pi-book', route: '/servicebook', viewPerm: 'view_service' },
  { label: 'Inventar', icon: 'pi pi-box', route: '/inventory', viewPerm: 'view_item' },
  { label: 'Bestellungen', icon: 'pi pi-shopping-cart', route: '/orders', viewPerm: 'view_order' },
  {
    label: 'Qualifikationen',
    icon: 'pi pi-certificate',
    route: '/qualifications',
    viewPerm: 'view_qualification'
  },
  {
    label: 'Ausbildung',
    icon: 'pi pi-calendar',
    route: '/training',
    viewPerm: 'view_trainingsession'
  }
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

onMounted(async () => {
  try {
    await Promise.allSettled([
      authStore.canAccessModule('view_member') ? membersStore.fetchMembers() : Promise.resolve([]),
      authStore.canAccessModule('view_parent') ? parentsStore.fetchParents() : Promise.resolve([]),
      authStore.canAccessModule('view_qualification')
        ? qualificationsStore.fetchStatistics()
        : Promise.resolve(null),
      authStore.canAccessModule('view_service')
        ? servicebookStore.fetchChartData()
        : Promise.resolve(null)
    ])

    stats.value = {
      totalMembers: membersStore.pagination.count,
      totalParents: parentsStore.pagination.count,
      totalQualifications: qualificationsStore.statistics?.total_qualifications || 0,
      expiringQualifications: qualificationsStore.statistics?.expiring_qualifications || 0
    }
  } catch {
  }
})
</script>

<style scoped>
.attendance-chart-wrapper {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.attendance-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1rem;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.875rem;
  color: var(--p-text-muted-color, #64748b);
}

.legend-color {
  width: 0.75rem;
  height: 0.75rem;
  border-radius: 999px;
}

.legend-color--present {
  background: #22c55e;
}

.legend-color--excused {
  background: #f59e0b;
}

.legend-color--absent {
  background: #ef4444;
}

.attendance-chart-grid {
  display: flex;
  gap: 0.35rem;
  align-items: end;
  min-width: max-content;
}

.attendance-chart-scroll {
  overflow-x: auto;
  padding-bottom: 0.35rem;
}

.attendance-column {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.attendance-total {
  font-size: 0.75rem;
  color: var(--p-text-muted-color, #64748b);
  min-height: 1rem;
}

.attendance-bar {
  width: 0.9rem;
  height: 10rem;
  border-radius: 0.35rem;
  overflow: hidden;
  display: flex;
  flex-direction: column-reverse;
  background: color-mix(in srgb, var(--p-surface-400, #94a3b8) 20%, transparent);
}

.attendance-segment {
  width: 100%;
  transition: height 0.2s ease-in-out;
}

.attendance-segment--present {
  background: #22c55e;
}

.attendance-segment--excused {
  background: #f59e0b;
}

.attendance-segment--absent {
  background: #ef4444;
}

.attendance-month {
  font-size: 0.62rem;
  color: var(--p-text-muted-color, #64748b);
  text-transform: uppercase;
  letter-spacing: 0.02em;
  writing-mode: vertical-rl;
  transform: rotate(180deg);
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: 0.75rem;
}

.module-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 7rem;
  border: 1px solid color-mix(in srgb, var(--p-primary-color, #2563eb) 30%, transparent);
  border-radius: 0.75rem;
  background: color-mix(in srgb, var(--p-primary-color, #2563eb) 8%, transparent);
  cursor: pointer;
  color: var(--p-text-color, #111827);
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease,
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.module-tile:hover,
.module-tile:focus-visible {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgb(0 0 0 / 10%);
  border-color: var(--p-primary-color, #2563eb);
  background: color-mix(in srgb, var(--p-primary-color, #2563eb) 15%, transparent);
}

.module-icon {
  font-size: 1.5rem;
}

.module-label {
  text-align: center;
  font-weight: 600;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .attendance-bar {
    height: 8.5rem;
  }
}
</style>


