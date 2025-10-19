<script setup lang="ts">
import { ref, computed, onMounted, watch, onBeforeUnmount } from 'vue'
import { useQualificationsStore } from '@/stores/qualifications'
import { useMembersStore } from '@/stores/members'
import { useUsersStore } from '@/stores/users'
import type { Qualification, QualificationListParams } from '@/types/qualifications'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'

interface Props {
  showFilters?: boolean
  showPagination?: boolean
  pageSize?: number
  statusFilter?: 'all' | 'active' | 'expired' | 'expiring'
  sortField?: string
  sortOrder?: 1 | -1
}

const props = withDefaults(defineProps<Props>(), {
  showFilters: true,
  showPagination: true,
  pageSize: 20,
  statusFilter: 'all',
  sortField: 'date_expires',
  sortOrder: 1
})

const emit = defineEmits<{
  view: [qualificationId: number]
  edit: [qualificationId: number]
  delete: [qualificationId: number]
}>()

const qualificationsStore = useQualificationsStore()
const membersStore = useMembersStore()
const usersStore = useUsersStore()

// Filter state
const filters = ref({
  search: '',
  member: null as number | null,
  user: null as number | null,
  type: null as number | null,
  status: props.statusFilter
})

// Pagination state
const first = ref(0)
const rows = ref(props.pageSize)
const sortField = ref(props.sortField)
const sortOrder = ref(props.sortOrder)

// Local table state
const tableData = ref<Qualification[]>([])
const totalRecords = ref(0)
const isLoading = ref(false)
let searchDebounceHandle: ReturnType<typeof setTimeout> | null = null

// Options for filters
const memberOptions = computed(() => {
  return [
    { label: 'Alle Personen', value: null },
    ...membersStore.members.map(member => ({
      label: member.full_name,
      value: member.id
    }))
  ]
})

const typeOptions = computed(() => {
  return [
    { label: 'Alle Typen', value: null },
    ...qualificationsStore.qualificationTypes.map(type => ({
      label: type.name,
      value: type.id
    }))
  ]
})

const userOptions = computed(() => {
  return [
    { label: 'Alle Benutzer', value: null },
    ...usersStore.users.map(user => ({
      label: user.full_name || user.username,
      value: user.id
    }))
  ]
})

const statusOptions = [
  { label: 'Alle', value: 'all' },
  { label: 'Gültig', value: 'active' },
  { label: 'Läuft bald ab', value: 'expiring' },
  { label: 'Abgelaufen', value: 'expired' }
]

// Load data
onMounted(async () => {
  await Promise.all([
    qualificationsStore.fetchQualificationTypes(),
    membersStore.fetchMembers({ limit: 1000 }),
    usersStore.fetchUsers({ limit: 1000, is_active: true })
  ])
  await fetchQualifications()
})

async function fetchQualifications() {
  isLoading.value = true

  try {
    const params: QualificationListParams = {
      page: Math.floor(first.value / rows.value) + 1,
      page_size: rows.value,
      search: filters.value.search || undefined,
      member: filters.value.member || undefined,
      user: filters.value.user || undefined,
      type: filters.value.type || undefined,
      status: filters.value.status !== 'all' ? filters.value.status : undefined,
      ordering: sortOrder.value === 1 ? sortField.value : `-${sortField.value}`
    }

    const results = await qualificationsStore.fetchQualifications(params)
    tableData.value = Array.isArray(results) ? [...results] : []
    totalRecords.value = qualificationsStore.qualificationsTotal
  } finally {
    isLoading.value = false
  }
}

// Event handlers
function onPage(event: any) {
  first.value = event.first
  rows.value = event.rows
  fetchQualifications()
}

function onSort(event: any) {
  sortField.value = event.sortField || props.sortField
  sortOrder.value = event.sortOrder || props.sortOrder
  first.value = 0
  fetchQualifications()
}

function clearFilters() {
  filters.value = {
    search: '',
    member: null,
    user: null,
    type: null,
    status: 'all'
  }
  first.value = 0
  sortField.value = props.sortField
  sortOrder.value = props.sortOrder
  fetchQualifications()
}

// Prop watchers to keep local state in sync
watch(
  () => props.sortField,
  (newField) => {
    sortField.value = newField
    fetchQualifications()
  }
)

watch(
  () => props.sortOrder,
  (newOrder) => {
    sortOrder.value = newOrder
  }
)

watch(
  () => props.statusFilter,
  (newStatus) => {
    filters.value.status = newStatus
    first.value = 0
  }
)

watch(
  () => props.pageSize,
  (newSize) => {
    rows.value = newSize
    first.value = 0
    fetchQualifications()
  }
)

// Apply filters automatically
watch(
  () => [filters.value.member, filters.value.user, filters.value.type, filters.value.status],
  () => {
    first.value = 0
    fetchQualifications()
  }
)

watch(
  () => filters.value.search,
  () => {
    if (searchDebounceHandle) {
      clearTimeout(searchDebounceHandle)
    }
    searchDebounceHandle = setTimeout(() => {
      first.value = 0
      fetchQualifications()
    }, 350)
  }
)

onBeforeUnmount(() => {
  if (searchDebounceHandle) {
    clearTimeout(searchDebounceHandle)
  }
})

function reload(reset = false) {
  if (reset) {
    first.value = 0
  }
  return fetchQualifications()
}

defineExpose({ reload })

// Status helpers
function getStatusSeverity(qualification: Qualification): 'success' | 'warning' | 'danger' {
  if (qualification.is_expired) return 'danger'
  if (qualification.expires_soon) return 'warning'
  return 'success'
}

function getStatusLabel(qualification: Qualification): string {
  if (qualification.is_expired) return 'Abgelaufen'
  if (qualification.expires_soon) return 'Läuft bald ab'
  return 'Gültig'
}

function getRowClass(qualification: Qualification) {
  if (qualification.is_expired) return 'row-expired'
  if (qualification.expires_soon) return 'row-expiring'
  return ''
}

function getDaysUntilExpiry(qualification: Qualification): string {
  if (!qualification.date_expires) return 'Unbegrenzt'
  if (qualification.is_expired) return '-'
  
  const now = new Date()
  const expires = new Date(qualification.date_expires)
  const diffTime = expires.getTime() - now.getTime()
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  
  return `${diffDays} Tage`
}

function formatDate(dateString: string | null): string {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE')
}

function handleView(qualification: Qualification) {
  emit('view', qualification.id)
}

function handleEdit(qualification: Qualification) {
  emit('edit', qualification.id)
}

function handleDelete(qualification: Qualification) {
  emit('delete', qualification.id)
}
</script>

<template>
  <div class="qualifications-table-container">
    <!-- Filters -->
    <div v-if="showFilters" class="filters-panel">
      <div class="filters-grid">
        <div class="filter-field">
          <label for="search">Suche</label>
          <InputText
            id="search"
            v-model="filters.search"
            placeholder="Person, Typ..."
          />
        </div>

        <div class="filter-field">
          <label for="member">Person</label>
          <Dropdown
            id="member"
            v-model="filters.member"
            :options="memberOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Person wählen"
            filter
            showClear
          />
        </div>

        <div class="filter-field">
          <label for="user">Benutzer</label>
          <Dropdown
            id="user"
            v-model="filters.user"
            :options="userOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Benutzer wählen"
            filter
            showClear
          />
        </div>

        <div class="filter-field">
          <label for="type">Typ</label>
          <Dropdown
            id="type"
            v-model="filters.type"
            :options="typeOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Typ wählen"
            showClear
          />
        </div>

        <div class="filter-field">
          <label for="status">Status</label>
          <Dropdown
            id="status"
            v-model="filters.status"
            :options="statusOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Status wählen"
          />
        </div>
      </div>

      <div class="filter-actions">
        <Button label="Zurücksetzen" icon="pi pi-times" severity="secondary" outlined @click="clearFilters" />
      </div>
    </div>

    <!-- Data Table -->
    <DataTable
      :value="tableData"
      :loading="isLoading"
      :totalRecords="totalRecords"
      :lazy="true"
      :paginator="showPagination"
      :rows="rows"
      :first="first"
      @page="onPage"
      @sort="onSort"
      :sortField="sortField"
      :sortOrder="sortOrder"
      :rowClass="getRowClass"
      stripedRows
      responsiveLayout="stack"
      breakpoint="960px"
      scrollable
    >
      <template #empty>
        <div class="empty-state">
          <i class="pi pi-inbox" style="font-size: 2rem"></i>
          <p>Keine Qualifikationen gefunden</p>
        </div>
      </template>

      <template #loading>
        <ProgressSpinner />
      </template>

      <Column field="person_name" header="Person" sortable style="min-width: 150px">
        <template #body="{ data }">
          <strong>{{ data.person_name }}</strong>
        </template>
      </Column>

      <Column field="type_name" header="Typ" sortable style="min-width: 180px">
        <template #body="{ data }">
          {{ data.type_name }}
        </template>
      </Column>

      <Column field="date_acquired" header="Erwerbsdatum" sortable style="min-width: 120px">
        <template #body="{ data }">
          {{ formatDate(data.date_acquired) }}
        </template>
      </Column>

      <Column field="date_expires" header="Ablaufdatum" sortable style="min-width: 120px">
        <template #body="{ data }">
          {{ formatDate(data.date_expires) }}
        </template>
      </Column>

      <Column header="Status" style="min-width: 120px">
        <template #body="{ data }">
          <Tag :severity="getStatusSeverity(data)" :value="getStatusLabel(data)" />
        </template>
      </Column>

      <Column header="Tage bis Ablauf" style="min-width: 140px">
        <template #body="{ data }">
          <span :class="{ 'text-danger': data.is_expired, 'text-warning': data.expires_soon }">
            {{ getDaysUntilExpiry(data) }}
          </span>
        </template>
      </Column>

      <Column header="Aktionen" style="min-width: 180px">
        <template #body="{ data }">
          <div class="action-buttons">
            <Button
              icon="pi pi-eye"
              severity="info"
              size="small"
              text
              rounded
              @click="handleView(data)"
              v-tooltip.top="'Details'"
            />
            <Button
              icon="pi pi-pencil"
              severity="secondary"
              size="small"
              text
              rounded
              @click="handleEdit(data)"
              v-tooltip.top="'Bearbeiten'"
            />
            <Button
              icon="pi pi-trash"
              severity="danger"
              size="small"
              text
              rounded
              @click="handleDelete(data)"
              v-tooltip.top="'Löschen'"
            />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.qualifications-table-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.filters-panel {
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.filters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.filter-field label {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-color);
}

.filter-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--text-color-secondary);
}

.empty-state i {
  margin-bottom: 1rem;
  color: var(--text-color-secondary);
}

.text-danger {
  color: var(--red-500);
  font-weight: 600;
}

.text-warning {
  color: var(--yellow-600, #ca8a04);
  font-weight: 600;
}

.row-expiring {
  background-color: rgba(250, 204, 21, 0.18);
}

.row-expired {
  background-color: rgba(248, 113, 113, 0.16);
}

/* Mobile responsiveness */
@media (max-width: 768px) {
  .filters-grid {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    flex-direction: column;
  }

  .filter-actions :deep(.p-button) {
    width: 100%;
  }
}
</style>
