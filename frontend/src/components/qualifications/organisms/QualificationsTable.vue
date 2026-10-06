<script setup lang="ts">
import { ref, computed, onMounted, watch, onBeforeUnmount } from 'vue'
import { useQualificationsStore } from '@/stores/qualifications'
import { useMembersStore } from '@/stores/members'
import { useUsersStore } from '@/stores/users'
import type { Qualification, QualificationListParams } from '@/types/qualifications'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { formatDate, qualificationStatus } from '../utils/qualificationStatus'

interface Props {
  showFilters?: boolean
  showPagination?: boolean
  pageSize?: number
  statusFilter?: 'all' | 'active' | 'expired' | 'expiring'
  sortField?: string
  sortOrder?: 1 | -1
  /** Extra list parameters chosen by the page, e.g. an expiry window (UX-06.2). */
  query?: Partial<QualificationListParams>
}

const props = withDefaults(defineProps<Props>(), {
  showFilters: true,
  showPagination: true,
  pageSize: 20,
  statusFilter: 'all',
  sortField: 'date_expires',
  sortOrder: 1,
  query: () => ({})
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
      ordering: sortOrder.value === 1 ? sortField.value : `-${sortField.value}`,
      ...props.query
    }

    const results = await qualificationsStore.fetchQualifications(params)
    tableData.value = Array.isArray(results) ? [...results] : []
    totalRecords.value = qualificationsStore.qualificationsTotal
  } finally {
    isLoading.value = false
  }
}

// Event handlers
function onPage(event: { first: number; rows: number }) {
  first.value = event.first
  rows.value = event.rows
  fetchQualifications()
}

function onSort(event: import('primevue/datatable').DataTableSortEvent) {
  const sf = event.sortField
  sortField.value = (typeof sf === 'string' ? sf : undefined) || props.sortField
  sortOrder.value = (event.sortOrder as 1 | -1) || props.sortOrder
  first.value = 0
  fetchQualifications()
}

function clearFilters() {
  filters.value = {
    search: '',
    member: null,
    user: null,
    type: null,
    status: props.statusFilter
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
  () => props.query,
  () => {
    first.value = 0
    fetchQualifications()
  },
  { deep: true }
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
          <Select
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
          <Select
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
          <Select
            id="type"
            v-model="filters.type"
            :options="typeOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Typ wählen"
            showClear
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
      stripedRows
      responsiveLayout="stack"
      breakpoint="960px"
      scrollable
    >
      <template #empty>
        <StateView kind="empty" title="Keine Qualifikationen in dieser Ansicht" message="Passe Ansicht oder Filter an." />
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

      <Column header="Gültigkeit" style="min-width: 200px">
        <template #body="{ data }">
          <div class="validity">
            <StatusBadge v-bind="qualificationStatus(data)" />
            <StatusBadge v-if="data.has_evidence === false" label="Nachweis fehlt" severity="neutral" icon="pi pi-file" />
          </div>
        </template>
      </Column>

      <Column header="Aktionen" style="min-width: 140px">
        <template #body="{ data }">
          <div class="action-buttons">
            <Button icon="pi pi-eye" severity="secondary" size="small" text rounded :aria-label="`${data.type_name} von ${data.person_name} ansehen`" v-tooltip.top="'Ansehen'" @click="handleView(data)" />
            <Button icon="pi pi-pencil" severity="secondary" size="small" text rounded :aria-label="`${data.type_name} von ${data.person_name} bearbeiten`" v-tooltip.top="'Bearbeiten'" @click="handleEdit(data)" />
            <Button icon="pi pi-trash" severity="danger" size="small" text rounded :aria-label="`${data.type_name} von ${data.person_name} löschen`" v-tooltip.top="'Löschen'" @click="handleDelete(data)" />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.qualifications-table-container { display: flex; flex-direction: column; gap: var(--jf-space-2); }

.filters-panel { display: flex; flex-wrap: wrap; align-items: flex-end; gap: var(--jf-space-2); }
.filters-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--jf-space-2);
}
.filter-field { display: flex; flex-direction: column; gap: var(--jf-space-0-5); }
.filter-field label { font-size: var(--jf-text-sm); font-weight: var(--jf-weight-semibold); color: var(--jf-color-text); }
.filter-actions { display: flex; gap: var(--jf-space-1); }

.validity { display: flex; flex-wrap: wrap; gap: var(--jf-space-0-5); }
.action-buttons { display: flex; gap: var(--jf-space-0-5); }
</style>
