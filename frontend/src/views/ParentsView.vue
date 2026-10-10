<template>
  <div class="parents-view">
    <OverviewHeader title="Eltern" :subtitle="subtitle">
      <template #actions>
        <Button
          label="E-Mail an diese Seite"
          icon="pi pi-envelope"
          severity="secondary"
          outlined
          :disabled="!parentsStore.emailAllParentsLink"
          @click="emailAllParents"
        />
        <Button v-if="!isMobile" label="Elternteil anlegen" icon="pi pi-plus" @click="navigateToCreate" />
      </template>
    </OverviewHeader>

    <Card class="filters-card">
      <template #content>
        <IconField>
          <InputIcon class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            placeholder="Name oder E-Mail suchen …"
            aria-label="Eltern suchen"
            class="w-full"
            @input="handleSearch"
          />
        </IconField>
      </template>
    </Card>

    <StateView v-if="loadState === 'loading'" kind="loading" title="Eltern werden geladen …" />
    <StateView
      v-else-if="loadState"
      :kind="loadState"
      :title="loadState === 'forbidden' ? 'Keine Berechtigung für Eltern' : 'Eltern konnten nicht geladen werden'"
      :retry="loadState !== 'forbidden'"
      @retry="fetchParents"
    />

    <Card v-else-if="!isMobile" class="table-card">
      <template #content>
        <DataTable
          :value="parentsStore.parents"
          :loading="parentsStore.loading"
          lazy
          paginator
          :rows="currentRows"
          :first="tableFirst"
          :total-records="parentsStore.pagination.count"
          :rows-per-page-options="[10, 20, 50]"
          paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
          current-page-report-template="{first} bis {last} von {totalRecords}"
          :sort-field="sortField"
          :sort-order="sortOrder"
          class="clickable-rows"
          @page="onPage"
          @sort="onSort"
          @row-click="(event) => navigateToEdit(event.data)"
        >
          <Column field="lastname" header="Name" sortable>
            <template #body="{ data }">
              <span class="parent-name">{{ data.full_name || `${data.name} ${data.lastname}` }}</span>
            </template>
          </Column>
          <Column header="E-Mail">
            <template #body="{ data }"><ContactLink kind="email" :value="data.email" /></template>
          </Column>
          <Column header="Telefon">
            <template #body="{ data }"><ContactLink kind="phone" :value="data.phone" /></template>
          </Column>
          <Column header="Mobil">
            <template #body="{ data }"><ContactLink kind="phone" :value="data.mobile" /></template>
          </Column>
          <Column header="Verknüpft">
            <template #body="{ data }"><ParentLinkBadge :parent="data" /></template>
          </Column>
          <Column :style="{ width: '7rem' }">
            <template #header><span class="sr-only">Aktionen</span></template>
            <template #body="{ data }">
              <div class="table-actions">
                <Button
                  icon="pi pi-pencil"
                  text
                  rounded
                  severity="secondary"
                  :aria-label="`${data.full_name} bearbeiten`"
                  v-tooltip.top="'Bearbeiten'"
                  @click.stop="navigateToEdit(data)"
                />
                <Button
                  icon="pi pi-trash"
                  text
                  rounded
                  severity="danger"
                  :aria-label="`${data.full_name} löschen`"
                  v-tooltip.top="'Löschen'"
                  @click.stop="confirmDelete(data)"
                />
              </div>
            </template>
          </Column>
          <template #empty>
            <StateView kind="empty" title="Keine Eltern gefunden" :message="emptyMessage" />
          </template>
        </DataTable>
      </template>
    </Card>

    <ResponsiveList
      v-else
      :items="parentsStore.parents"
      :loading="parentsStore.loading"
      :rows="currentRows"
      :paginator="parentsStore.pagination.count > currentRows"
      :total-records="parentsStore.pagination.count"
      :lazy="true"
      item-key="id"
      @page="onPage"
    >
      <template #item="{ item }">
        <ParentCard :parent="item as Parent" @edit="navigateToEdit" @delete="confirmDelete" />
      </template>
      <template #empty>
        <StateView kind="empty" title="Keine Eltern gefunden" :message="emptyMessage" />
      </template>
    </ResponsiveList>

    <router-link v-if="isMobile" to="/parents/create" class="create-fab">
      <i class="pi pi-plus" aria-hidden="true"></i>Anlegen
    </router-link>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable, { type DataTableSortEvent } from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import ContactLink from '@/components/common/ContactLink.vue'
import ResponsiveList from '@/components/common/ResponsiveList.vue'
import StateView, { stateForError, type StateKind } from '@/components/common/StateView.vue'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import ParentCard from '@/components/parents/ParentCard.vue'
import ParentLinkBadge from '@/components/parents/ParentLinkBadge.vue'
import { useMobile } from '@/composables/useMobile'
import { useQueryTableState } from '@/composables/useQueryTableState'
import { useDepartmentsStore } from '@/stores/departments'
import { useParentsStore } from '@/stores/parents'
import type { Parent } from '@/types/parents'
import { classifyApiError, getApiErrorMessage } from '@/utils/apiError'

const URL_DEFAULTS = { page: 1, rows: 20, sortField: 'lastname', sortOrder: 1 }
const SORT_FIELDS = ['lastname', 'name']

const router = useRouter()
const parentsStore = useParentsStore()
const departmentsStore = useDepartmentsStore()
const confirm = useConfirm()
const toast = useToast()
const { isMobile } = useMobile()
const { getInt, getString, syncToUrl } = useQueryTableState()

const searchQuery = ref(getString('search'))
const currentPage = ref(Math.max(1, getInt('page', 1)))
const currentRows = ref(getInt('rows', 20))
const sortField = ref(SORT_FIELDS.includes(getString('sortField')) ? getString('sortField') : 'lastname')
const sortOrder = ref<1 | -1>(getInt('sortOrder', 1) === -1 ? -1 : 1)
const tableFirst = computed(() => (currentPage.value - 1) * currentRows.value)
/** null once data is shown; otherwise the state the list area displays. */
const loadState = ref<StateKind | null>(parentsStore.parents.length ? null : 'loading')

const subtitle = computed(() => {
  const count = parentsStore.pagination.count
  const department = departmentsStore.activeDepartment
  const scope = department ? ` in ${department.code}` : ''
  if (loadState.value === 'loading') return 'Eltern werden geladen …'
  return `${count} ${count === 1 ? 'Kontakt' : 'Kontakte'}${scope}`
})

const emptyMessage = computed(() =>
  searchQuery.value ? 'Passe die Suche an oder lege einen neuen Eintrag an.' : 'Lege den ersten Elternkontakt an.',
)

function persist() {
  syncToUrl(
    {
      search: searchQuery.value,
      page: currentPage.value,
      rows: currentRows.value,
      sortField: sortField.value,
      sortOrder: sortOrder.value,
    },
    URL_DEFAULTS,
  )
}

async function fetchParents() {
  if (!parentsStore.parents.length) loadState.value = 'loading'
  try {
    await parentsStore.fetchParents({
      offset: tableFirst.value,
      limit: currentRows.value,
      search: searchQuery.value || undefined,
      ordering: sortOrder.value === -1 ? `-${sortField.value}` : sortField.value,
    })
    loadState.value = null
  } catch (error) {
    loadState.value = stateForError(classifyApiError(error))
  }
}

let searchTimeout: ReturnType<typeof setTimeout> | undefined
function handleSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    persist()
    fetchParents()
  }, 400)
}

function onPage(event: { page: number; rows: number }) {
  currentPage.value = event.page + 1
  currentRows.value = event.rows
  persist()
  fetchParents()
}

function onSort(event: DataTableSortEvent) {
  const field = typeof event.sortField === 'string' && SORT_FIELDS.includes(event.sortField) ? event.sortField : 'lastname'
  sortField.value = field
  sortOrder.value = event.sortOrder === -1 ? -1 : 1
  currentPage.value = 1
  persist()
  fetchParents()
}

function navigateToCreate() {
  router.push('/parents/create')
}

function navigateToEdit(parent: Parent) {
  router.push(`/parents/${parent.id}/edit`)
}

function emailAllParents() {
  const mailtoLink = parentsStore.emailAllParentsLink
  if (mailtoLink) window.location.href = mailtoLink
}

function confirmDelete(parent: Parent) {
  confirm.require({
    message: `Möchtest du ${parent.full_name || `${parent.name} ${parent.lastname}`} wirklich löschen? Verknüpfungen zu Mitgliedern gehen dabei verloren.`,
    header: 'Elternteil löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: () => deleteParent(parent.id),
  })
}

async function deleteParent(id: number) {
  try {
    await parentsStore.deleteParent(id)
    toast.add({ severity: 'success', summary: 'Gelöscht', detail: 'Elternteil wurde gelöscht', life: 3000 })
    fetchParents()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Nicht gelöscht',
      detail: getApiErrorMessage(error, 'Elternteil konnte nicht gelöscht werden'),
      life: 5000,
    })
  }
}

onMounted(fetchParents)
</script>

<style scoped>
.parents-view {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: var(--jf-space-6);
}

.parents-view :deep(.overview-header) {
  margin-bottom: 0;
}

.filters-card :deep(.p-card-body) {
  padding: var(--jf-space-2);
}

.table-card {
  overflow: hidden;
}

.table-card :deep(.p-card-body) {
  padding: 0;
}

.table-card :deep(.p-datatable-tbody > tr > td) {
  padding-block: var(--jf-space-1-5);
}

.parent-name {
  font-weight: var(--jf-weight-semibold);
}

.table-actions {
  display: flex;
  gap: var(--jf-space-0-5);
  justify-content: flex-end;
}

.clickable-rows :deep(tbody tr) {
  cursor: pointer;
}

.clickable-rows :deep(tbody tr:hover) {
  background-color: var(--surface-hover);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.create-fab {
  position: fixed;
  right: var(--jf-space-2);
  bottom: calc(80px + env(safe-area-inset-bottom, 0px));
  z-index: 950;
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: 56px;
  padding: 0 var(--jf-space-3);
  border-radius: 16px;
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
  box-shadow: var(--jf-shadow-lg);
}

@media (max-width: 767px) {
  .parents-view {
    gap: var(--jf-space-1);
  }

  .parents-view :deep(.overview-header) {
    flex-wrap: wrap;
    gap: var(--jf-space-1);
    padding: 0;
  }

  .filters-card :deep(.p-card-body) {
    padding: var(--jf-space-1-5);
  }
}
</style>
