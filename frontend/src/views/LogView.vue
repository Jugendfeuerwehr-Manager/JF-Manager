<template>
  <div class="log-master-detail">
    <!-- Left sidebar: Event Type categories -->
    <div class="log-sidebar">
      <div class="log-sidebar-header">
        <span class="font-semibold text-lg">Kategorien</span>
      </div>
      <div class="log-sidebar-list">
        <!-- "All entries" entry -->
        <div
          class="log-sidebar-item"
          :class="{ 'log-sidebar-item--active': selectedTypeId === null }"
          @click="selectType(null)"
        >
          <span class="log-sidebar-item-name">Alle Einträge</span>
          <Badge v-if="totalAllCount > 0" :value="totalAllCount" severity="secondary" />
        </div>
        <!-- Individual event types -->
        <div
          v-for="eventType in eventTypes"
          :key="eventType.id"
          class="log-sidebar-item"
          :class="{ 'log-sidebar-item--active': selectedTypeId === eventType.id }"
          @click="selectType(eventType.id)"
        >
          <span class="log-sidebar-item-name">{{ eventType.name }}</span>
          <Badge v-if="eventType.event_count" :value="eventType.event_count" severity="secondary" />
        </div>
      </div>
    </div>

    <!-- Right panel: Events table -->
    <div class="log-content">
      <!-- Header -->
      <div class="log-content-header mb-3">
        <div>
          <h1 class="text-2xl font-bold m-0">
            {{ selectedType ? selectedType.name : 'Alle Einträge' }}
          </h1>
          <p class="text-color-secondary mt-1 mb-0">Protokolleinträge</p>
        </div>
        <div class="log-header-actions">
          <Button
            label="Liste erstellen"
            icon="pi pi-list"
            @click="openCreateListDialog"
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
      </div>

      <!-- Filters -->
      <div class="filters-row mb-3">
        <span class="p-input-icon-left search-input">
          <i class="pi pi-search" />
          <InputText
            v-model="search"
            placeholder="Suche nach Mitglied oder Notiz…"
            class="w-full"
            @input="onSearchInput"
          />
        </span>
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
      </div>

      <!-- Desktop Table -->
      <Card class="log-table-card">
        <template #content>
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

            <Column v-if="selectedTypeId === null" field="event_type" header="Typ" style="min-width: 130px">
              <template #body="{ data }">
                <Tag
                  v-if="data.event_type"
                  :value="formatEventTypeLabel(data.event_type)"
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
                  v-if="event.event_type && selectedTypeId === null"
                  :value="formatEventTypeLabel(event.event_type)"
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

    <!-- Create List Dialog -->
    <Dialog
      v-model:visible="showCreateListDialog"
      modal
      header="Liste aus Protokollfilter erstellen"
      style="width: min(500px, 95vw)"
    >
      <div class="flex flex-column gap-4 pt-1">
        <div class="field">
          <label class="font-semibold block mb-2">Listenname *</label>
          <InputText
            v-model="newListName"
            class="w-full"
            placeholder="z.B. DSGVO-Unterschriften"
            autofocus
          />
        </div>

        <div class="field">
          <label class="font-semibold block mb-2">Datumsbereich (optional)</label>
          <div class="flex gap-2">
            <DatePicker
              v-model="dateFrom"
              date-format="dd.mm.yy"
              placeholder="Von"
              class="flex-1"
              show-clear
              update-model-type="date"
            />
            <DatePicker
              v-model="dateTo"
              date-format="dd.mm.yy"
              placeholder="Bis"
              class="flex-1"
              show-clear
              update-model-type="date"
            />
          </div>
        </div>

        <div class="field">
          <div class="flex align-items-center gap-3">
            <ToggleSwitch v-model="invertSelection" input-id="invert-toggle" />
            <label for="invert-toggle" class="font-semibold cursor-pointer">Umgekehrte Auswahl</label>
          </div>
          <p class="text-sm text-color-secondary mt-2 mb-0">{{ invertDescription }}</p>
        </div>

        <div class="filter-summary surface-100 border-round p-3">
          <p class="text-sm m-0 text-color-secondary">
            <i class="pi pi-info-circle mr-1"></i>{{ filterSummary }}
          </p>
        </div>
      </div>

      <template #footer>
        <Button label="Abbrechen" text severity="secondary" @click="showCreateListDialog = false" />
        <Button
          label="Liste erstellen"
          icon="pi pi-check"
          :loading="creatingList"
          :disabled="!newListName.trim()"
          @click="submitCreateList"
        />
      </template>
    </Dialog>

    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useEventsStore } from '@/stores/events'
import { useMembersStore } from '@/stores/members'
import { useMemberListsStore } from '@/stores/lists'
import { useDepartmentsStore } from '@/stores/departments'
import { eventsApi } from '@/api/members'
import type { Event, EventType } from '@/types/events'
import { useQueryTableState } from '@/composables/useQueryTableState'
import { useToast } from 'primevue/usetoast'
import Badge from 'primevue/badge'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import type { DataTablePageEvent, DataTableSortEvent } from 'primevue/datatable'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import Toast from 'primevue/toast'

const eventsStore = useEventsStore()
const membersStore = useMembersStore()
const listsStore = useMemberListsStore()
const departmentsStore = useDepartmentsStore()
const router = useRouter()
const toast = useToast()
const { getInt, getString, syncToUrl } = useQueryTableState()

// ── Category selection ────────────────────────────────────────────────────
const selectedTypeId = ref<number | null>(null)
const eventTypes = computed(() => eventsStore.eventTypes)
const selectedType = computed<EventType | null>(() =>
  selectedTypeId.value !== null
    ? (eventTypes.value.find((t) => t.id === selectedTypeId.value) ?? null)
    : null,
)

// ── Events table ──────────────────────────────────────────────────────────
const events = ref<Event[]>([])
const loading = ref(false)
const totalCount = ref(0)
const totalAllCount = ref(0)
const pageSize = ref(getInt('rows', 25))
const currentPage = ref(getInt('page', 1) - 1)
const sortField = ref(getString('sortField', 'datetime'))
const sortOrder = ref<-1 | 1>((getInt('sortOrder', -1)) as -1 | 1)

const search = ref(getString('search'))
const filterMember = ref<number | null>(getInt('member', 0) || null)

const LOG_URL_DEFAULTS = { page: 1, rows: 25, sortField: 'datetime', sortOrder: -1 }
let searchTimeout: ReturnType<typeof setTimeout> | null = null

const memberOptions = computed(() =>
  membersStore.members.map((m) => ({ label: m.full_name, value: m.id })),
)

function formatDate(dateStr: string) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

function formatEventTypeLabel(eventType: EventType | null) {
  if (!eventType) return '—'
  return eventType.department === null ? `${eventType.name} (Global)` : eventType.name
}

function selectType(typeId: number | null) {
  selectedTypeId.value = typeId
  currentPage.value = 0
  syncToUrl(
    { search: search.value, member: filterMember.value, page: 1, rows: pageSize.value, sortField: sortField.value, sortOrder: sortOrder.value },
    LOG_URL_DEFAULTS,
  )
  loadEvents()
}

async function loadEvents() {
  loading.value = true
  try {
    const ordering = (sortOrder.value === -1 ? '-' : '') + sortField.value
    const response = await eventsApi.list({
      search: search.value || undefined,
      type: selectedTypeId.value ?? undefined,
      member: filterMember.value ?? undefined,
      ordering,
      limit: pageSize.value,
      offset: currentPage.value * pageSize.value,
    })
    events.value = response.data.results
    totalCount.value = response.data.count
  } finally {
    loading.value = false
  }
}

async function loadTotalAllCount() {
  try {
    const response = await eventsApi.list({ limit: 1, offset: 0 })
    totalAllCount.value = response.data.count
  } catch {
    // non-critical
  }
}

function onSearchInput() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 0
    syncToUrl(
      { search: search.value, member: filterMember.value, page: 1, rows: pageSize.value, sortField: sortField.value, sortOrder: sortOrder.value },
      LOG_URL_DEFAULTS,
    )
    loadEvents()
  }, 350)
}

function onPage(event: DataTablePageEvent) {
  currentPage.value = event.page
  pageSize.value = event.rows
  syncToUrl(
    { search: search.value, member: filterMember.value, page: event.page + 1, rows: event.rows, sortField: sortField.value, sortOrder: sortOrder.value },
    LOG_URL_DEFAULTS,
  )
  loadEvents()
}

function onSort(event: DataTableSortEvent) {
  sortField.value = (event.sortField as string) ?? 'datetime'
  sortOrder.value = (event.sortOrder as 1 | -1) ?? -1
  currentPage.value = 0
  syncToUrl(
    { search: search.value, member: filterMember.value, page: 1, rows: pageSize.value, sortField: sortField.value, sortOrder: sortOrder.value },
    LOG_URL_DEFAULTS,
  )
  loadEvents()
}

function onMemberFilterChange() {
  currentPage.value = 0
  syncToUrl(
    { search: search.value, member: filterMember.value, page: 1, rows: pageSize.value, sortField: sortField.value, sortOrder: sortOrder.value },
    LOG_URL_DEFAULTS,
  )
  loadEvents()
}

// ── Create List Dialog ────────────────────────────────────────────────────
const showCreateListDialog = ref(false)
const newListName = ref('')
const dateFrom = ref<Date | null>(null)
const dateTo = ref<Date | null>(null)
const invertSelection = ref(false)
const creatingList = ref(false)

const invertDescription = computed(() => {
  const typeName =
    selectedTypeId.value === null
      ? 'einem beliebigen Protokolleintrag'
      : (selectedType.value?.name ?? 'diesem Eintragstyp')
  const dateHint = dateFrom.value || dateTo.value ? ' (im gewählten Zeitraum)' : ''
  if (invertSelection.value) {
    return `Mitglieder, die KEINEN Eintrag vom Typ „${typeName}" haben${dateHint}.`
  }
  return `Mitglieder, die mindestens einen Eintrag vom Typ „${typeName}" haben${dateHint}.`
})

const filterSummary = computed(() => {
  const typeName =
    selectedTypeId.value === null ? 'Alle Eintragstypen' : (selectedType.value?.name ?? '')
  const parts = [`Kategorie: ${typeName}`]
  if (dateFrom.value) parts.push(`Von: ${dateFrom.value.toLocaleDateString('de-DE')}`)
  if (dateTo.value) parts.push(`Bis: ${dateTo.value.toLocaleDateString('de-DE')}`)
  if (invertSelection.value) parts.push('Auswahl umgekehrt')
  return parts.join(' · ')
})

function openCreateListDialog() {
  newListName.value = ''
  dateFrom.value = null
  dateTo.value = null
  invertSelection.value = false
  showCreateListDialog.value = true
}

async function submitCreateList() {
  if (!newListName.value.trim()) return
  creatingList.value = true
  try {
    const newList = await listsStore.createFromEventType({
      name: newListName.value.trim(),
      event_type_id: selectedTypeId.value,
      invert: invertSelection.value,
      date_from: dateFrom.value ? dateFrom.value.toISOString().split('T')[0] : null,
      date_to: dateTo.value ? dateTo.value.toISOString().split('T')[0] : null,
    })
    showCreateListDialog.value = false
    toast.add({
      severity: 'success',
      summary: 'Liste erstellt',
      detail: `„${newList.name}" wurde erstellt.`,
      life: 3000,
    })
    router.push({ name: 'list-detail', params: { id: newList.id } })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Die Liste konnte nicht erstellt werden.',
      life: 4000,
    })
  } finally {
    creatingList.value = false
  }
}

onMounted(async () => {
  await Promise.all([eventsStore.fetchEventTypes(), membersStore.fetchMembers({ limit: 1000 })])
  loadEvents()
  loadTotalAllCount()
})

watch(() => departmentsStore.activeDepartmentId, async () => {
  eventsStore.invalidateEventTypesCache()
  await Promise.all([eventsStore.fetchEventTypes(), membersStore.fetchMembers({ limit: 1000 })])
  currentPage.value = 0
  loadEvents()
  loadTotalAllCount()
})
</script>

<style scoped>
/* ── Master-detail layout ─────────────────────────────────────────────── */
.log-master-detail {
  display: flex;
  gap: 1.25rem;
  height: calc(100vh - 8rem);
  min-height: 0;
}

/* ── Left sidebar ────────────────────────────────────────────────────── */
.log-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--p-surface-0);
  border: 1px solid var(--p-surface-200);
  border-radius: var(--p-border-radius-md, 6px);
  overflow: hidden;
}

.log-sidebar-header {
  padding: 1rem 1rem 0.75rem;
  border-bottom: 1px solid var(--p-surface-200);
}

.log-sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0;
}

.log-sidebar-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  cursor: pointer;
  border-radius: 0;
  transition: background 0.15s;
}

.log-sidebar-item:hover {
  background: var(--p-surface-100);
}

.log-sidebar-item--active {
  background: var(--p-primary-50, #eff6ff);
  color: var(--p-primary-600, #2563eb);
  font-weight: 600;
  border-left: 3px solid var(--p-primary-500, #3b82f6);
}

.log-sidebar-item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.9rem;
}

/* ── Right content panel ─────────────────────────────────────────────── */
.log-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.log-content-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.log-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

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

.log-table-card {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

/* ── Table / card states ─────────────────────────────────────────────── */
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

.notes-cell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 280px;
}

.member-link {
  color: var(--p-primary-color);
  text-decoration: none;
}

.member-link:hover {
  text-decoration: underline;
}

/* ── Mobile ──────────────────────────────────────────────────────────── */
.mobile-log-list {
  display: none;
}

.mobile-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

@media (max-width: 768px) {
  .log-master-detail {
    flex-direction: column;
    height: auto;
  }

  .log-sidebar {
    width: 100%;
    max-height: 180px;
  }

  .log-sidebar-list {
    display: flex;
    flex-direction: row;
    flex-wrap: nowrap;
    overflow-x: auto;
    padding: 0.25rem 0.5rem;
    gap: 0.25rem;
  }

  .log-sidebar-item {
    flex-shrink: 0;
    border-radius: 1rem;
    padding: 0.4rem 0.75rem;
    border: 1px solid var(--p-surface-200);
    white-space: nowrap;
  }

  .log-sidebar-item--active {
    border-left: 1px solid var(--p-primary-500, #3b82f6);
    border-color: var(--p-primary-500, #3b82f6);
  }

  .log-table-card {
    display: none;
  }

  .mobile-log-list {
    display: block;
  }

  .mobile-event-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
}
</style>
