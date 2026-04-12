<template>
  <div class="event-log-view">
    <div class="log-header mb-4">
      <h1 class="text-3xl font-bold">Protokoll</h1>
      <p class="text-color-secondary">Alle Mitgliedereinträge auf einen Blick</p>
    </div>

    <!-- Filters toolbar -->
    <Card class="filters-card mb-4">
      <template #content>
        <div class="filters-row">
          <span class="p-input-icon-left search-input">
            <i class="pi pi-search" />
            <InputText
              v-model="search"
              placeholder="Suche nach Mitglied, Typ oder Notiz…"
              class="w-full"
              @input="onSearchInput"
            />
          </span>

          <Select
            v-model="filterType"
            :options="eventTypeOptions"
            option-label="label"
            option-value="value"
            placeholder="Eintragstyp"
            show-clear
            class="filter-select"
            @change="onTypeFilterChange"
          />

          <Select
            v-model="filterMember"
            :options="memberOptions"
            option-label="label"
            option-value="value"
            placeholder="Mitglied"
            show-clear
            filter
            class="filter-select"
            @change="onMemberFilterChange"
          />

          <Button
            icon="pi pi-refresh"
            severity="secondary"
            text
            rounded
            v-tooltip.top="'Aktualisieren'"
            :loading="loading"
            @click="loadEvents"
          />
        </div>
      </template>
    </Card>

    <!-- Data Table -->
    <Card>
      <template #content>
        <!-- Desktop Table -->
        <DataTable
          :value="events"
          :loading="loading"
          :rows="pageSize"
          :first="currentPage * pageSize"
          lazy
          :total-records="totalCount"
          paginator
          paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown"
          :rows-per-page-options="[10, 25, 50]"
          current-page-report-template="{first} bis {last} von {totalRecords}"
          responsive-layout="scroll"
          striped-rows
          @page="onPage"
          @sort="onSort"
          class="log-table"
        >
          <template #empty>
            <div class="empty-state">
              <i class="pi pi-list"></i>
              <p>Keine Einträge gefunden</p>
            </div>
          </template>

          <Column field="datetime" header="Datum" sortable style="min-width: 140px">
            <template #body="{ data }">
              <span class="date-cell">
                <i class="pi pi-calendar mr-1 text-color-secondary"></i>
                {{ formatDate(data.datetime) }}
              </span>
            </template>
          </Column>

          <Column field="member_name" header="Mitglied" sortable style="min-width: 160px">
            <template #body="{ data }">
              <RouterLink
                v-if="data.member"
                :to="`/members/${data.member}`"
                class="member-link"
              >
                <i class="pi pi-user mr-1"></i>
                {{ data.member_name }}
              </RouterLink>
              <span v-else>{{ data.member_name }}</span>
            </template>
          </Column>

          <Column field="event_type" header="Typ" style="min-width: 130px">
            <template #body="{ data }">
              <Tag
                v-if="data.event_type"
                :value="data.event_type.name"
                severity="info"
              />
              <span v-else class="text-color-secondary">—</span>
            </template>
          </Column>

          <Column field="notes" header="Notizen" style="min-width: 250px">
            <template #body="{ data }">
              <div v-if="data.notes" class="notes-cell" v-tooltip.top="data.notes">
                {{ data.notes }}
              </div>
              <span v-else class="text-color-secondary">—</span>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Mobile Card List -->
    <div class="mobile-log-list">
      <div v-if="loading" class="flex justify-content-center p-4">
        <ProgressSpinner style="width: 2rem; height: 2rem" />
      </div>

      <div v-else-if="!events.length" class="empty-state">
        <i class="pi pi-list"></i>
        <p>Keine Einträge gefunden</p>
      </div>

      <template v-else>
        <Card v-for="event in events" :key="event.id" class="mobile-event-card mb-2">
          <template #content>
            <div class="mobile-event-header">
              <RouterLink
                v-if="event.member"
                :to="`/members/${event.member}`"
                class="member-link font-semibold"
              >
                {{ event.member_name }}
              </RouterLink>
              <span v-else class="font-semibold">{{ event.member_name }}</span>
              <Tag
                v-if="event.event_type"
                :value="event.event_type.name"
                severity="info"
                class="ml-auto"
              />
            </div>
            <div class="mobile-event-date text-color-secondary text-sm mt-1">
              <i class="pi pi-calendar mr-1"></i>
              {{ formatDate(event.datetime) }}
            </div>
            <div v-if="event.notes" class="mobile-event-notes mt-2">
              {{ event.notes }}
            </div>
          </template>
        </Card>

        <!-- Mobile Pagination -->
        <div class="mobile-pagination mt-3">
          <Button
            icon="pi pi-chevron-left"
            severity="secondary"
            text
            :disabled="currentPage === 0"
            @click="currentPage--; loadEvents()"
          />
          <span class="text-color-secondary text-sm">
            Seite {{ currentPage + 1 }} von {{ Math.ceil(totalCount / pageSize) || 1 }}
          </span>
          <Button
            icon="pi pi-chevron-right"
            severity="secondary"
            text
            :disabled="(currentPage + 1) * pageSize >= totalCount"
            @click="currentPage++; loadEvents()"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useEventsStore } from '@/stores/events'
import { useMembersStore } from '@/stores/members'
import { eventsApi } from '@/api/members'
import type { Event } from '@/types/api'
import { useQueryTableState } from '@/composables/useQueryTableState'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import type { DataTablePageEvent, DataTableSortEvent } from 'primevue/datatable'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'

const eventsStore = useEventsStore()
const membersStore = useMembersStore()
const { getInt, getString, syncToUrl } = useQueryTableState()

const events = ref<Event[]>([])
const loading = ref(false)
const totalCount = ref(0)
const pageSize = ref(getInt('rows', 25))
const currentPage = ref(getInt('page', 1) - 1)  // DataTable uses 0-indexed page
const sortField = ref(getString('sortField', 'datetime'))
const sortOrder = ref<-1 | 1>((getInt('sortOrder', -1)) as -1 | 1)

const search = ref(getString('search'))
const filterType = ref<number | null>(getInt('type', 0) || null)
const filterMember = ref<number | null>(getInt('member', 0) || null)

const LOG_URL_DEFAULTS = { page: 1, rows: 25, sortField: 'datetime', sortOrder: -1 }

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const eventTypeOptions = computed(() =>
  eventsStore.eventTypeOptions
)

const memberOptions = computed(() =>
  membersStore.members.map(m => ({ label: m.full_name, value: m.id }))
)

function formatDate(dateStr: string) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

async function loadEvents() {
  loading.value = true
  try {
    const ordering = (sortOrder.value === -1 ? '-' : '') + sortField.value
    const response = await eventsApi.list({
      search: search.value || undefined,
      type: filterType.value ?? undefined,
      member: filterMember.value ?? undefined,
      ordering,
      limit: pageSize.value,
      offset: currentPage.value * pageSize.value
    })
    events.value = response.data.results
    totalCount.value = response.data.count
  } finally {
    loading.value = false
  }
}

function onSearchInput() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 0
    syncToUrl({ search: search.value, type: filterType.value, member: filterMember.value, page: currentPage.value + 1, rows: pageSize.value, sortField: sortField.value, sortOrder: sortOrder.value }, LOG_URL_DEFAULTS)
    loadEvents()
  }, 350)
}

function onPage(event: DataTablePageEvent) {
  currentPage.value = event.page
  pageSize.value = event.rows
  syncToUrl({ search: search.value, type: filterType.value, member: filterMember.value, page: currentPage.value + 1, rows: pageSize.value, sortField: sortField.value, sortOrder: sortOrder.value }, LOG_URL_DEFAULTS)
  loadEvents()
}

function onSort(event: DataTableSortEvent) {
  sortField.value = (event.sortField as string) ?? 'datetime'
  sortOrder.value = (event.sortOrder as 1 | -1) ?? -1
  currentPage.value = 0
  syncToUrl({ search: search.value, type: filterType.value, member: filterMember.value, page: currentPage.value + 1, rows: pageSize.value, sortField: sortField.value, sortOrder: sortOrder.value }, LOG_URL_DEFAULTS)
  loadEvents()
}

function onTypeFilterChange() {
  currentPage.value = 0
  syncToUrl({ search: search.value, type: filterType.value, member: filterMember.value, page: currentPage.value + 1, rows: pageSize.value, sortField: sortField.value, sortOrder: sortOrder.value }, LOG_URL_DEFAULTS)
  loadEvents()
}

function onMemberFilterChange() {
  currentPage.value = 0
  syncToUrl({ search: search.value, type: filterType.value, member: filterMember.value, page: currentPage.value + 1, rows: pageSize.value, sortField: sortField.value, sortOrder: sortOrder.value }, LOG_URL_DEFAULTS)
  loadEvents()
}

onMounted(async () => {
  await Promise.all([
    eventsStore.fetchEventTypes(),
    membersStore.fetchMembers({ limit: 1000 })
  ])
  loadEvents()
})
</script>

<style scoped>
.filters-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 200px;
}

.filter-select {
  min-width: 160px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem;
  color: var(--p-text-muted-color);
}

.empty-state i {
  font-size: 2rem;
}

.date-cell {
  white-space: nowrap;
}

.member-link {
  color: var(--p-primary-color);
  text-decoration: none;
  font-weight: 500;
}

.member-link:hover {
  text-decoration: underline;
}

/* Notes: readable multi-line with clamp */
.notes-cell {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
  max-width: 400px;
  font-size: 0.875rem;
  color: var(--p-text-color);
  cursor: help;
}

/* Mobile card list hidden on desktop */
.mobile-log-list {
  display: none;
}

/* Desktop table visible on larger screens */
.log-table {
  display: block;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .filters-row {
    flex-direction: column;
  }

  .search-input,
  .filter-select {
    width: 100%;
    min-width: unset;
  }

  /* Hide desktop table, show mobile cards */
  .log-table {
    display: none !important;
  }

  :deep(.p-card .p-card-body) {
    padding: 0.75rem;
  }

  .mobile-log-list {
    display: block;
  }

  .mobile-event-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .mobile-event-notes {
    background: var(--p-surface-50);
    border-radius: var(--p-border-radius);
    padding: 0.5rem 0.75rem;
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.6;
    font-size: 0.875rem;
    color: var(--p-text-color);
  }

  .mobile-pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
  }
}
</style>
