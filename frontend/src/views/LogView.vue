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
            @change="loadEvents"
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
            @change="loadEvents"
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
        <DataTable
          :value="events"
          :loading="loading"
          :rows="pageSize"
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

          <Column field="notes" header="Notizen" style="min-width: 200px">
            <template #body="{ data }">
              <span v-if="data.notes" class="notes-cell">{{ data.notes }}</span>
              <span v-else class="text-color-secondary">—</span>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useEventsStore } from '@/stores/events'
import { useMembersStore } from '@/stores/members'
import { eventsApi } from '@/api/members'
import type { Event } from '@/types/api'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import type { DataTablePageEvent, DataTableSortEvent } from 'primevue/datatable'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'

const eventsStore = useEventsStore()
const membersStore = useMembersStore()

const events = ref<Event[]>([])
const loading = ref(false)
const totalCount = ref(0)
const pageSize = ref(25)
const currentPage = ref(0)
const sortField = ref('datetime')
const sortOrder = ref<-1 | 1>(-1)

const search = ref('')
const filterType = ref<number | null>(null)
const filterMember = ref<number | null>(null)

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
    loadEvents()
  }, 350)
}

function onPage(event: DataTablePageEvent) {
  currentPage.value = event.page
  pageSize.value = event.rows
  loadEvents()
}

function onSort(event: DataTableSortEvent) {
  sortField.value = (event.sortField as string) ?? 'datetime'
  sortOrder.value = (event.sortOrder as 1 | -1) ?? -1
  currentPage.value = 0
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

.notes-cell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
  display: block;
}
</style>
