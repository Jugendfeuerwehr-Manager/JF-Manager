<template>
  <div class="servicebook-list-view">
    <Toolbar class="view-toolbar">
      <template #start>
        <div class="toolbar-title">
          <h1>Dienstbuch</h1>
          <p>Verwaltung der Dienste und Anwesenheiten</p>
        </div>
      </template>
      <template #end>
        <Button
          label="Neuer Dienst"
          icon="pi pi-plus"
          @click="handleCreate"
        />
      </template>
    </Toolbar>

    <!-- Statistics Panel (collapsible) -->
    <Panel header="Statistiken" :collapsed="true" toggleable class="mb-4">
      <div v-if="statisticsLoading" class="loading-container">
        <ProgressSpinner />
      </div>
      <div v-else-if="statistics" class="statistics-grid">
        <!-- Top Lists -->
        <Card v-for="(list, key) in topLists" :key="key" class="top-list-card">
          <template #title>{{ list.title }}</template>
          <template #content>
            <div v-if="!list.data || list.data.length === 0" class="empty-list">
              Keine Daten verfügbar
            </div>
            <div v-else class="list-items">
              <div v-for="(item, index) in list.data" :key="index" class="list-item">
                <span class="rank">{{ index + 1 }}.</span>
                <span class="name">{{ item.person__name }} {{ item.person__lastname }}</span>
                <Tag :value="item.num_services" />
              </div>
            </div>
          </template>
        </Card>
      </div>
    </Panel>

    <!-- Filters -->
    <Card class="mb-4">
      <template #content>
        <ServiceFilters
          :filters="filters"
          @update:filters="filters = $event"
          @apply="applyFilters"
        />
      </template>
    </Card>

    <!-- Services List -->
    <ServicesList
      :services="servicebookStore.services"
      :loading="servicebookStore.servicesLoading"
      :error="servicebookStore.servicesError"
      :total-records="servicebookStore.servicesTotalCount"
      :current-page="currentPage"
      :page-size="pageSize"
      @view="handleView"
      @edit="handleEdit"
      @create="handleCreate"
      @page-change="handlePageChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onActivated, computed } from 'vue'
import { useRouter } from 'vue-router'
import Toolbar from 'primevue/toolbar'
import Button from 'primevue/button'
import Panel from 'primevue/panel'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import ServicesList from '@/components/servicebook/organisms/ServicesList.vue'
import ServiceFilters from '@/components/servicebook/molecules/ServiceFilters.vue'
import { useServicebookStore } from '@/stores/servicebook'
import type { ServiceFilters as ServiceFiltersType, ServiceListParams } from '@/types/servicebook'

const router = useRouter()
const servicebookStore = useServicebookStore()

const filters = ref<ServiceFiltersType>({
  search: undefined,
  topic: undefined,
  place: undefined,
  operations_manager: undefined,
  dateFrom: null,
  dateTo: null
})

const currentPage = ref(1)
const pageSize = ref(12)
const statisticsLoading = ref(false)
const statistics = ref(servicebookStore.statistics)

onMounted(async () => {
  await loadServices()
  await loadStatistics()
})

// Refetch services when returning to this view
onActivated(async () => {
  await loadServices()
})

const loadServices = async () => {
  const params: ServiceListParams = {
    page: currentPage.value,
    page_size: pageSize.value,
    ordering: '-start'
  }

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

const loadStatistics = async () => {
  statisticsLoading.value = true
  try {
    await servicebookStore.fetchStatistics()
    statistics.value = servicebookStore.statistics
  } catch (error) {
    console.error('Failed to load statistics:', error)
  } finally {
    statisticsLoading.value = false
  }
}

const topLists = computed(() => {
  if (!statistics.value) {
    return {
      present: { title: 'Am meisten anwesend', data: [] },
      excused: { title: 'Am meisten entschuldigt', data: [] },
      absent: { title: 'Am meisten fehlend', data: [] }
    }
  }

  return {
    present: {
      title: 'Am meisten anwesend',
      data: statistics.value.top_lists.most_present || []
    },
    excused: {
      title: 'Am meisten entschuldigt',
      data: statistics.value.top_lists.most_excused || []
    },
    absent: {
      title: 'Am meisten fehlend',
      data: statistics.value.top_lists.most_absent || []
    }
  }
})

const applyFilters = async () => {
  currentPage.value = 1
  await loadServices()
}

const handlePageChange = async (page: number, size: number) => {
  currentPage.value = page
  pageSize.value = size
  await loadServices()
}

const handleView = (id: number) => {
  router.push({ name: 'service-detail', params: { id } })
}

const handleEdit = (id: number) => {
  router.push({ name: 'service-edit', params: { id } })
}

const handleCreate = () => {
  router.push({ name: 'service-create' })
}
</script>

<style scoped>
.view-toolbar {
  margin-bottom: 1.5rem;
  border-radius: var(--border-radius);
}

.toolbar-title h1 {
  margin: 0 0 0.25rem 0;
  font-size: 1.75rem;
  font-weight: 600;
}

.toolbar-title p {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 0.95rem;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 2rem;
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.list-items {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  background: var(--surface-50);
  border-radius: var(--border-radius);
}

.list-item .rank {
  font-weight: 700;
  color: var(--primary-color);
  min-width: 1.5rem;
}

.list-item .name {
  flex: 1;
  font-weight: 500;
}

.empty-list {
  text-align: center;
  padding: 2rem;
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .toolbar-title h1 {
    font-size: 1.5rem;
  }

  .statistics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
