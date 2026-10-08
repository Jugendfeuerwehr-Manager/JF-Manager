<template>
  <div class="servicebook-list-view">
    <OverviewHeader title="Dienstbuch" subtitle="Dienste planen, Anwesenheit erfassen und nachbereiten">
      <template #actions>
        <Button
          v-if="canViewReport"
          label="Auswertung"
          icon="pi pi-chart-bar"
          severity="secondary"
          outlined
          @click="router.push({ name: 'service-report' })"
        />
        <Button label="Neuer Dienst" icon="pi pi-plus" class="create-button" @click="handleCreate" />
      </template>
    </OverviewHeader>

    <ServiceMobileList v-if="isMobile" :department="departmentsStore.activeDepartmentId" />

    <template v-else>
    <section v-if="todayServices.length" class="today" aria-labelledby="today-title">
      <h2 id="today-title" class="visually-hidden">Heute</h2>
      <article v-for="service in todayServices" :key="service.id" class="today-card">
        <div class="today-card__top">
          <span class="today-card__when">{{ todayStatus(service) }}</span>
          <StatusBadge
            v-if="service.attendance_summary && attendanceCount(service)"
            severity="success"
            icon="pi pi-users"
            :label="`${service.attendance_summary.present} anwesend`"
          />
        </div>
        <h3 class="today-card__title">{{ service.topic || 'Dienst ohne Thema' }}</h3>
        <p class="today-card__meta">{{ [timeRange(service), service.place].filter(Boolean).join(' · ') }}</p>
        <div class="today-card__actions">
          <router-link
            v-if="service.training_session"
            :to="{ name: 'training-run', params: { id: service.training_session } }"
            class="today-action today-action--primary"
          >
            <i class="pi pi-play" aria-hidden="true"></i>Durchführen
          </router-link>
          <router-link
            :to="{ name: 'service-attendance', params: { id: service.id } }"
            class="today-action"
            :class="{ 'today-action--primary': !service.training_session }"
          >
            <i class="pi pi-check-square" aria-hidden="true"></i>Anwesenheit erfassen
          </router-link>
        </div>
      </article>
    </section>

    <div class="list-controls">
      <SegmentedControl
        class="scope-switch"
        label="Zeitraum"
        :model-value="scope"
        :options="[{ value: 'upcoming', label: 'Kommend' }, { value: 'past', label: 'Vergangen' }]"
        @update:model-value="setScope"
      />
      <Button
        :label="activeFilterCount ? `Filter (${activeFilterCount})` : 'Filter'"
        icon="pi pi-filter"
        severity="secondary"
        outlined
        aria-controls="service-filters"
        :aria-expanded="filtersOpen"
        @click="filtersOpen = !filtersOpen"
      />
    </div>

    <section v-if="filtersOpen" id="service-filters" class="filters-card" aria-label="Filter">
      <ServiceFilters
        :filters="filters"
        @update:filters="filters = $event"
        @apply="applyFilters"
      />
    </section>

    <ServicesList
      :services="servicebookStore.services"
      :loading="servicebookStore.servicesLoading"
      :error="servicebookStore.servicesError"
      :total-records="servicebookStore.servicesTotalCount"
      :current-page="currentPage"
      :page-size="pageSize"
      :empty-title="scope === 'upcoming' ? 'Keine kommenden Dienste' : 'Keine vergangenen Dienste'"
      :empty-message="activeFilterCount ? 'Für die gewählten Filter gibt es keine Treffer.' : ''"
      @view="handleView"
      @edit="handleEdit"
      @create="handleCreate"
      @open-training="handleOpenTraining"
      @page-change="handlePageChange"
    />
    </template>
  </div>
</template>

<script setup lang="ts">
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import { ref, onMounted, onActivated, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import ServiceMobileList from '@/components/servicebook/organisms/ServiceMobileList.vue'
import { useMobile } from '@/composables/useMobile'
import { useDepartmentsStore } from '@/stores/departments'
import ServicesList from '@/components/servicebook/organisms/ServicesList.vue'
import ServiceFilters from '@/components/servicebook/molecules/ServiceFilters.vue'
import { useServicebookStore } from '@/stores/servicebook'
import { useAuthStore } from '@/stores/auth'
import type { ServiceFilters as ServiceFiltersType, ServiceListParams } from '@/types/servicebook'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import { useQueryTableState } from '@/composables/useQueryTableState'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { servicesApi } from '@/api/servicebook'
import type { Service } from '@/types/servicebook'

const router = useRouter()
const servicebookStore = useServicebookStore()
const authStore = useAuthStore()
const departmentsStore = useDepartmentsStore()
/** PART-02.2: below 768px the servicebook shows the mobile list instead of the table list. */
const { isMobile } = useMobile(768)
const canViewReport = computed(() => authStore.hasPerm('servicebook.view_attendance') || authStore.hasPerm('servicebook.change_attendance'))
const { getInt, getString, syncToUrl } = useQueryTableState()

const filters = ref<ServiceFiltersType>({
  search: getString('search') || undefined,
  topic: getString('topic') || undefined,
  place: getString('place') || undefined,
  operations_manager: getInt('operations_manager', 0) || undefined,
  dateFrom: getString('dateFrom') ? new Date(getString('dateFrom')) : null,
  dateTo: getString('dateTo') ? new Date(getString('dateTo')) : null
})

const currentPage = ref(getInt('page', 1))
const pageSize = ref(getInt('rows', 12))

const SERVICES_URL_DEFAULTS = { page: 1, rows: 12, scope: 'upcoming' }
const scope = ref<'upcoming' | 'past'>(getString('scope') === 'past' ? 'past' : 'upcoming')
const filtersOpen = ref(false)
const todayServices = ref<Service[]>([])
const activeFilterCount = computed(() => [
  filters.value.search, filters.value.topic, filters.value.place, filters.value.operations_manager,
  filters.value.dateFrom, filters.value.dateTo,
].filter(Boolean).length)

async function loadDesktop() {
  if (isMobile.value) return
  await Promise.all([loadServices(), loadToday()])
}

onMounted(async () => {
  filtersOpen.value = activeFilterCount.value > 0
  await loadDesktop()
})

// Refetch services when returning to this view
onActivated(loadDesktop)
watch(isMobile, (mobile) => { if (!mobile) void loadDesktop() })

/** Today's services get their own card with the direct way to take attendance. */
async function loadToday() {
  const from = new Date()
  from.setHours(0, 0, 0, 0)
  const to = new Date(from)
  to.setHours(23, 59, 59, 999)
  try {
    const { data } = await servicesApi.list({ start__gte: from.toISOString(), start__lte: to.toISOString(), ordering: 'start', limit: 3 })
    todayServices.value = data.results
  } catch {
    todayServices.value = []
  }
}

function timeRange(service: Service) {
  const time = (value: string) => new Date(value).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  return `${time(service.start)}–${time(service.end)}`
}

function attendanceCount(service: Service) {
  const summary = service.attendance_summary
  return summary.present + summary.excused + summary.absent
}

function todayStatus(service: Service) {
  const now = Date.now()
  const start = new Date(service.start).getTime()
  const end = new Date(service.end).getTime()
  if (now < start) {
    const minutes = Math.round((start - now) / 60000)
    return minutes < 60 ? `Heute · beginnt in ${minutes} Min.` : `Heute · ab ${timeRange(service).split('–')[0]} Uhr`
  }
  if (now <= end) return 'Heute · läuft gerade'
  return 'Heute · beendet'
}

function urlState() {
  return { search: filters.value.search, topic: filters.value.topic, place: filters.value.place, operations_manager: filters.value.operations_manager, dateFrom: filters.value.dateFrom?.toISOString().split('T')[0], dateTo: filters.value.dateTo?.toISOString().split('T')[0], page: currentPage.value, rows: pageSize.value, scope: scope.value }
}

async function setScope(next: 'upcoming' | 'past') {
  if (scope.value === next) return
  scope.value = next
  currentPage.value = 1
  syncToUrl(urlState(), SERVICES_URL_DEFAULTS)
  await loadServices()
}

const loadServices = async () => {
  const params: ServiceListParams = {
    offset: (currentPage.value - 1) * pageSize.value,
    limit: pageSize.value,
    ordering: scope.value === 'upcoming' ? 'start' : '-start'
  }
  const now = new Date().toISOString()
  if (scope.value === 'upcoming') params.end__gte = now
  else params.end__lte = now

  if (filters.value.search) {
    params.search = filters.value.search
  }
  if (filters.value.topic) {
    params.topic = filters.value.topic
  }
  if (filters.value.place) {
    params.place = filters.value.place
  }
  if (filters.value.operations_manager) {
    params.operations_manager = filters.value.operations_manager
  }
  if (filters.value.dateFrom) {
    params.start__gte = filters.value.dateFrom.toISOString()
  }
  if (filters.value.dateTo) {
    params.start__lte = filters.value.dateTo.toISOString()
  }

  await servicebookStore.fetchServices(params)
}

const applyFilters = async () => {
  currentPage.value = 1
  syncToUrl(urlState(), SERVICES_URL_DEFAULTS)
  await loadServices()
}

const handlePageChange = async (page: number, size: number) => {
  currentPage.value = page
  pageSize.value = size
  syncToUrl(urlState(), SERVICES_URL_DEFAULTS)
  await loadServices()
}

const handleView = (id: number) => {
  router.push({ name: 'service-attendance', params: { id } })
}

const handleEdit = (id: number) => {
  router.push({ name: 'service-edit', params: { id } })
}

const handleCreate = () => {
  router.push({ name: 'service-create' })
}

const handleOpenTraining = (trainingId: number) => {
  router.push({ name: 'training-planner', params: { id: trainingId } })
}
</script>

<style scoped>
.servicebook-list-view {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  max-width: 1100px;
  margin: 0 auto;
}

.servicebook-list-view :deep(.overview-header) {
  margin-bottom: 0;
  padding-bottom: 0;
}

.today {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--jf-space-2);
}

.today-card {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  padding: var(--jf-space-2) var(--jf-space-3);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  box-shadow: var(--jf-shadow-sm);
}

.today-card__top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
}

.today-card__when {
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--jf-color-primary);
}

.today-card__title {
  margin: 0;
  font-size: var(--jf-text-lg);
}

.today-card__meta {
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.today-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1);
  margin-top: var(--jf-space-1);
}

.today-action {
  flex: 1 1 160px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--jf-space-1);
  min-height: 48px;
  padding: 0 var(--jf-space-2);
  border: 1px solid var(--p-surface-300);
  border-radius: var(--jf-radius-md);
  color: var(--jf-color-text);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}

.today-action--primary {
  border-color: var(--jf-color-primary);
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
}

.list-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1);
}

.scope-switch {
  flex: 1 1 260px;
  max-width: 420px;
}

.filters-card {
  padding: var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

@media (max-width: 1023px) {
  .create-button {
    position: fixed;
    right: var(--jf-space-2);
    bottom: calc(80px + env(safe-area-inset-bottom, 0px));
    z-index: 950;
    min-height: 56px;
    border-radius: 16px;
    box-shadow: var(--jf-shadow-lg);
  }
}
</style>
