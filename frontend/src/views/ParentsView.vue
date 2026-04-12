<template>
  <div class="parents-view">
    <OverviewHeader
      title="Eltern"
      subtitle="Verwaltung der Elternkontakte"
    >
      <template #actions>
        <Button
          :label="isMobile ? '' : 'E-Mail an alle'"
          icon="pi pi-envelope"
          @click="emailAllParents"
          :disabled="!parentsStore.emailAllParentsLink"
          severity="secondary"
          outlined
          class="mr-2"
        />
        <Button
          :label="isMobile ? '' : 'Hinzufügen'"
          icon="pi pi-plus"
          @click="navigateToCreate"
          severity="primary"
        />
      </template>
    </OverviewHeader>

    <!-- Filters -->
    <Card class="filters-card">
      <template #content>
        <IconField icon-position="left">
          <InputIcon class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            placeholder="Name, E-Mail oder Telefon..."
            @input="handleSearch"
            class="w-full"
          />
        </IconField>
      </template>
    </Card>

    <!-- Loading State -->
    <div v-if="parentsStore.loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <!-- Desktop: DataTable -->
    <Card v-else-if="!isMobile" class="desktop-table-card">
      <template #content>
        <DataTable
          :value="parentsStore.parents"
          paginator
          :rows="currentRows"
          :first="tableFirst"
          :total-records="parentsStore.pagination.count"
          :rows-per-page-options="[10, 20, 50]"
          lazy
          @page="onPage"
          striped-rows
          class="parents-table"
        >
          <Column field="name" header="Vorname" sortable />
          <Column field="lastname" header="Nachname" sortable />
          <Column field="email" header="E-Mail" />
          <Column field="phone" header="Telefon" />
          <Column field="mobile" header="Mobil" />
          <Column header="" style="width: 50px">
            <template #body="{ data }">
              <Tag
                v-if="data.children && data.children.length === 0"
                value="Kein Kind"
                severity="warn"
                v-tooltip.top="'Kein Mitglied mit diesem Elternteil verknüpft'"
              />
            </template>
          </Column>
          <Column header="Aktionen" style="width: 120px">
            <template #body="{ data }">
              <div class="table-actions">
                <Button
                  icon="pi pi-pencil"
                  rounded
                  text
                  @click="navigateToEdit(data)"
                  :title="'Bearbeiten'"
                />
                <Button
                  icon="pi pi-trash"
                  rounded
                  text
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

    <!-- Mobile: Responsive List -->
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
        <ParentCard
          :parent="item"
          @edit="navigateToEdit"
          @delete="confirmDelete"
        />
      </template>
      <template #empty>
        <div class="mobile-list-empty">
          <i class="pi pi-user"></i>
          <p>Keine Eltern gefunden</p>
        </div>
      </template>
    </ResponsiveList>

    <!-- Delete Confirmation -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useParentsStore } from '@/stores/parents'
import type { Parent } from '@/api/members'
import { useQueryTableState } from '@/composables/useQueryTableState'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import ResponsiveList from '@/components/common/ResponsiveList.vue'
import ParentCard from '@/components/parents/ParentCard.vue'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'

const router = useRouter()
const parentsStore = useParentsStore()
const confirm = useConfirm()
const toast = useToast()
const { getInt, getString, syncToUrl } = useQueryTableState()

const isMobile = ref(window.innerWidth < 768)
const searchQuery = ref(getString('search'))
const currentPage = ref(getInt('page', 1))
const currentRows = ref(getInt('rows', 20))
const tableFirst = computed(() => (currentPage.value - 1) * currentRows.value)

const URL_DEFAULTS = { page: 1, rows: 20 }

onMounted(() => {
  fetchParents()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
}

const fetchParents = async () => {
  try {
    await parentsStore.fetchParents({
      offset: (currentPage.value - 1) * currentRows.value,
      limit: currentRows.value,
      search: searchQuery.value || undefined
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Eltern konnten nicht geladen werden',
      life: 3000
    })
  }
}

let searchTimeout: ReturnType<typeof setTimeout> | undefined
const handleSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    syncToUrl({ search: searchQuery.value, page: currentPage.value, rows: currentRows.value }, URL_DEFAULTS)
    fetchParents()
  }, 500)
}

const onPage = (event: { page: number; rows: number }) => {
  currentPage.value = event.page + 1
  currentRows.value = event.rows
  syncToUrl({ search: searchQuery.value, page: currentPage.value, rows: currentRows.value }, URL_DEFAULTS)
  fetchParents()
}

const navigateToCreate = () => {
  router.push('/parents/create')
}

const navigateToEdit = (parent: Parent) => {
  router.push(`/parents/${parent.id}/edit`)
}

const emailAllParents = () => {
  const mailtoLink = parentsStore.emailAllParentsLink
  if (mailtoLink) {
    window.location.href = mailtoLink
  } else {
    toast.add({
      severity: 'warn',
      summary: 'Keine E-Mail-Adressen',
      detail: 'Es wurden keine E-Mail-Adressen gefunden',
      life: 3000
    })
  }
}

const confirmDelete = (parent: Parent) => {
  confirm.require({
    message: `Möchten Sie ${parent.name} ${parent.lastname} wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, löschen',
    rejectLabel: 'Abbrechen',
    accept: () => deleteParent(parent.id)
  })
}

const deleteParent = async (id: number) => {
  try {
    await parentsStore.deleteParent(id)
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: 'Elternteil wurde gelöscht',
      life: 3000
    })
    fetchParents()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Elternteil konnte nicht gelöscht werden',
      life: 3000
    })
  }
}
</script>


