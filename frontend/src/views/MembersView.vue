<template>
  <div class="members-view">
    <div class="header-section">
      <div class="header-content">
        <h1>Mitglieder</h1>
        <p class="text-muted">Verwaltung der Jugendfeuerwehr-Mitglieder</p>
      </div>
      <Button 
        label="Mitglied hinzufügen" 
        icon="pi pi-plus" 
        @click="navigateToCreate"
        severity="primary"
      />
    </div>

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
      <div v-if="membersStore.loading" class="loading-container">
        <i class="pi pi-spin pi-spinner" style="font-size: 2rem"></i>
      </div>
      
      <div v-else-if="membersStore.members.length === 0" class="empty-state">
        <i class="pi pi-users" style="font-size: 3rem; color: var(--text-color-secondary);"></i>
        <p>Keine Mitglieder gefunden</p>
      </div>

      <div v-else class="member-cards">
        <Card 
          v-for="member in membersStore.members" 
          :key="member.id" 
          class="member-card"
        >
          <template #content>
            <div class="member-card-header">
              <div class="member-info">
                <h3>{{ member.full_name }}</h3>
                <Tag 
                  v-if="member.status"
                  :value="member.status.name"
                  :style="{ backgroundColor: member.status.color, color: 'white' }"
                />
              </div>
            </div>
            
            <div class="member-card-details">
              <div class="detail-row">
                <span class="detail-label">
                  <i class="pi pi-calendar"></i>
                  Geburtstag:
                </span>
                <span class="detail-value">
                  {{ formatDate(member.birthday) }} ({{ member.age }})
                </span>
              </div>
            </div>

            <!-- Contact Parents Section (reusable) -->
            <ParentContacts :member="member" variant="compact" />

            <div class="member-card-actions">
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
      </div>

      <!-- Mobile Pagination -->
      <div v-if="membersStore.members.length > 0" class="mobile-pagination">
        <Button
          icon="pi pi-angle-left"
          :disabled="lazyParams.first === 0"
          outlined
          @click="onMobilePrevPage"
        />
        <span class="pagination-info">
          {{ lazyParams.first + 1 }} - {{ Math.min(lazyParams.first + lazyParams.rows, membersStore.pagination.count) }} 
          von {{ membersStore.pagination.count }}
        </span>
        <Button
          icon="pi pi-angle-right"
          :disabled="lazyParams.first + lazyParams.rows >= membersStore.pagination.count"
          outlined
          @click="onMobileNextPage"
        />
      </div>
    </div>

    <ConfirmDialog />
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
import ConfirmDialog from 'primevue/confirmdialog'
import Dialog from 'primevue/dialog'
import ParentContacts from '@/components/members/ParentContacts.vue'

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

const onMobilePrevPage = () => {
  if (lazyParams.first > 0) {
    lazyParams.first = Math.max(0, lazyParams.first - lazyParams.rows)
    loadLazyData()
  }
}

const onMobileNextPage = () => {
  if (lazyParams.first + lazyParams.rows < membersStore.pagination.count) {
    lazyParams.first += lazyParams.rows
    loadLazyData()
  }
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


</script>

<style scoped>
.members-view {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.header-content h1 {
  margin: 0 0 0.5rem 0;
  font-size: 2rem;
  font-weight: 600;
  color: var(--text-color);
}

.text-muted {
  color: var(--text-color-secondary);
  margin: 0;
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

/* Mobile/Desktop view toggle */
.mobile-view {
  display: none;
}

.desktop-view {
  display: block;
}

/* Mobile Card Styles */
.member-cards {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.member-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.member-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.member-card-header {
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--surface-border);
}

.member-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.member-info h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-color);
}

.member-card-details {
  margin-bottom: 1rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
}




.detail-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-color-secondary);
  font-weight: 500;
}

.detail-label i {
  color: var(--primary-color);
}

.detail-value {
  color: var(--text-color);
  font-weight: 500;
}

.member-card-actions {
  display: flex;
  gap: 0.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}

.member-card-actions :deep(.p-button) {
  flex: 1;
}

.mobile-pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 1.5rem;
  padding: 1rem;
  background: var(--surface-card);
  border-radius: var(--border-radius);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.pagination-info {
  font-weight: 500;
  color: var(--text-color);
  white-space: nowrap;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 3rem;
  color: var(--primary-color);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  text-align: center;
  gap: 1rem;
}

.empty-state p {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 1.1rem;
}

@media (max-width: 768px) {
  .members-view {
    padding: 1rem;
  }

  .header-section {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
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

  .member-card-actions {
    flex-wrap: wrap;
  }

  .member-card-actions :deep(.p-button) {
    flex: 1 1 calc(50% - 0.25rem);
    min-width: 0;
  }

  .member-card-actions :deep(.p-button:last-child) {
    flex: 1 1 100%;
  }
}
</style>
