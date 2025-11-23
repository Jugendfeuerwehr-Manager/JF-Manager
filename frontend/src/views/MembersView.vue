<template>
  <div class="members-view">
    <OverviewHeader
      title="Mitglieder"
      subtitle="Verwaltung der Jugendfeuerwehr-Mitglieder"
    >
      <template #actions>
        <Button
          label="Excel Export"
          icon="pi pi-file-excel"
          @click="handleExportExcel"
          severity="success"
          outlined
          :loading="membersStore.loading"
        />
        <Button
          label="Mitglied hinzufügen"
          icon="pi pi-plus"
          @click="navigateToCreate"
          severity="primary"
        />
      </template>
    </OverviewHeader>

    <Card class="filter-card">
      <template #content>
        <div class="filter-grid">
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText
              v-model="filters.search"
              placeholder="Suchen..."
              class="w-full"
              @input="onFilterChange"
            />
          </IconField>
          
          <Dropdown
            v-model="filters.status"
            :options="membersStore.statuses || []"
            option-label="name"
            option-value="id"
            placeholder="Status filtern"
            show-clear
            class="w-full"
            @change="onFilterChange"
          />
          
          <Dropdown
            v-model="filters.group"
            :options="membersStore.groups || []"
            option-label="name"
            option-value="id"
            placeholder="Gruppe filtern"
            show-clear
            class="w-full"
            @change="onFilterChange"
          />
        </div>
      </template>
    </Card>

    <!-- Desktop Table View -->
    <Card class="table-card desktop-view">
      <template #content>
        <DataTable
          v-model:filters="lazyParams.filters"
          :value="membersStore.members"
          :lazy="true"
          :paginator="true"
          :rows="lazyParams.rows"
          :total-records="membersStore.pagination.count"
          :loading="membersStore.loading"
          :rows-per-page-options="[10, 20, 50]"
          paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
          current-page-report-template="{first} bis {last} von {totalRecords}"
          striped-rows
          removable-sort
          @page="onPage"
          @sort="onSort"
          @row-click="onRowClick"
          class="clickable-rows"
        >
          <Column 
            field="name" 
            header="Vorname" 
            sortable
          />
          
          <Column 
            field="lastname" 
            header="Nachname" 
            sortable
          />
          
          <Column 
            field="birthday" 
            header="Geburtstag" 
            sortable
          >
            <template #body="{ data }">
              {{ formatDate(data.birthday) }} ({{ data.age }})
            </template>
          </Column>
        
          
          <Column 
            field="status" 
            header="Status"
          >
            <template #body="{ data }">
              <Tag 
                v-if="data.status"
                :value="data.status.name"
                :style="{ backgroundColor: data.status.color, color: 'white' }"
              />
            </template>
          </Column>
          
          <Column header="Aktionen" :style="{ width: '12rem' }">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  icon="pi pi-eye"
                  size="small"
                  text
                  rounded
                  @click="navigateToView(data)"
                  :title="'Ansehen'"
                />
                <Button
                  icon="pi pi-pencil"
                  size="small"
                  text
                  rounded
                  severity="secondary"
                  @click="navigateToEdit(data)"
                  :title="'Bearbeiten'"
                />
                <Button
                  icon="pi pi-trash"
                  size="small"
                  text
                  rounded
                  severity="danger"
                  @click="confirmDelete(data)"
                  :title="'Löschen'"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Mobile Card View -->
    <div class="mobile-view">
      <ResponsiveList
        :items="membersStore.members"
        :loading="membersStore.loading"
        :rows="lazyParams.rows"
        :paginator="membersStore.pagination.count > lazyParams.rows"
        :total-records="membersStore.pagination.count"
        :lazy="true"
        item-key="id"
        @page="onPage"
      >
        <template #item="{ item: member }">
          <Card
            class="member-card mobile-entity-card"
            @click="navigateToView(member)"
          >
            <template #content>
              <div class="mobile-entity-card__header">
                <div>
                  <h3 class="mobile-entity-card__title">{{ member.full_name }}</h3>
                  <p class="mobile-entity-card__meta">
                    {{ formatDate(member.birthday) }} · {{ member.age }} Jahre
                  </p>
                </div>
                <Tag
                  v-if="member.status"
                  :value="member.status.name"
                  :style="{ backgroundColor: member.status.color, color: 'white' }"
                />
              </div>

              <div class="mobile-entity-card__section">
                <div class="mobile-entity-card__row">
                  <span class="mobile-entity-card__label">
                    <i class="pi pi-calendar"></i>
                    Geburtstag
                  </span>
                  <span class="mobile-entity-card__value">
                    {{ formatDate(member.birthday) }} ({{ member.age }})
                  </span>
                </div>
              </div>

              <ParentContacts :member="member" variant="compact" />

              <div class="mobile-entity-card__actions" @click.stop>
                <Button
                  label="Ansehen"
                  icon="pi pi-eye"
                  size="small"
                  outlined
                  @click="navigateToView(member)"
                />
                <Button
                  label="Bearbeiten"
                  icon="pi pi-pencil"
                  size="small"
                  outlined
                  severity="secondary"
                  @click="navigateToEdit(member)"
                />
                <Button
                  icon="pi pi-trash"
                  size="small"
                  outlined
                  severity="danger"
                  @click="confirmDelete(member)"
                />
              </div>
            </template>
          </Card>
        </template>

        <template #empty>
          <div class="mobile-list-empty">
            <i class="pi pi-users"></i>
            <p>Keine Mitglieder gefunden</p>
          </div>
        </template>
      </ResponsiveList>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useMembersStore } from '@/stores/members'
import type { Member, Parent } from '@/types/api'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import ResponsiveList from '@/components/common/ResponsiveList.vue'
import ParentContacts from '@/components/members/ParentContacts.vue'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'

const router = useRouter()
const membersStore = useMembersStore()
const confirm = useConfirm()
const toast = useToast()

// Contact dialog
const showContactDialog = ref(false)
const selectedParent = ref<Parent | null>(null)

onUnmounted(() => {
  
})

const filters = reactive({
  search: '',
  status: null as number | null,
  group: null as number | null,
})

const lazyParams = reactive({
  first: 0,
  rows: 20,
  sortField: 'lastname',
  sortOrder: 1,
  filters: {}
})

let filterTimeout: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  await Promise.all([
    membersStore.fetchStatuses(),
    membersStore.fetchGroups()
  ])
  loadLazyData()
})

const loadLazyData = () => {
  const offset = lazyParams.first
  const limit = lazyParams.rows
  
  let ordering = ''
  if (lazyParams.sortField) {
    ordering = lazyParams.sortOrder === -1 ? `-${lazyParams.sortField}` : lazyParams.sortField
  }

  membersStore.fetchMembers({
    offset,
    limit,
    search: filters.search || undefined,
    status: filters.status || undefined,
    group: filters.group || undefined,
    ordering: ordering || undefined
  })
}

const onPage = (event: any) => {
  lazyParams.first = event.first
  lazyParams.rows = event.rows
  loadLazyData()
}

const onSort = (event: any) => {
  lazyParams.sortField = event.sortField
  lazyParams.sortOrder = event.sortOrder
  loadLazyData()
}

const onFilterChange = () => {
  if (filterTimeout) {
    clearTimeout(filterTimeout)
  }
  filterTimeout = setTimeout(() => {
    lazyParams.first = 0
    loadLazyData()
  }, 500)
}

const formatDate = (dateString: string | null) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const navigateToCreate = () => {
  router.push('/members/create')
}

const navigateToView = (member: Member) => {
  router.push(`/members/${member.id}`)
}

const navigateToEdit = (member: Member) => {
  router.push(`/members/${member.id}/edit`)
}

const onRowClick = (event: any) => {
  // Navigate to member detail when row is clicked
  const member = event.data as Member
  router.push(`/members/${member.id}`)
}

const confirmDelete = (member: Member) => {
  confirm.require({
    message: `Möchten Sie ${member.full_name} wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await membersStore.deleteMember(member.id)
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Mitglied wurde gelöscht',
          life: 3000
        })
        loadLazyData()
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Mitglied konnte nicht gelöscht werden',
          life: 3000
        })
      }
    }
  })
}

const handleExportExcel = async () => {
  try {
    await membersStore.exportExcel()
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: 'Mitgliederliste wurde erfolgreich exportiert',
      life: 3000
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Export fehlgeschlagen',
      life: 3000
    })
  }
}

</script>

<style scoped>
.members-view {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.filter-card {
  margin-bottom: 1.5rem;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.table-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

/* Clickable rows styling */
.clickable-rows :deep(tbody tr) {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.clickable-rows :deep(tbody tr:hover) {
  background-color: var(--surface-hover) !important;
}

/* Mobile/Desktop view toggle */
.mobile-view {
  display: none;
}

.desktop-view {
  display: block;
}

.member-card {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.member-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
}

@media (max-width: 768px) {
  .members-view {
    padding: 1rem;
  }

  .filter-grid {
    grid-template-columns: 1fr;
  }

  /* Hide desktop table on mobile */
  .desktop-view {
    display: none;
  }

  /* Show mobile cards on mobile */
  .mobile-view {
    display: block;
  }
}
</style>
