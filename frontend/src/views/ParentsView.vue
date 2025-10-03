<template>
  <div class="parents-view">
    <!-- Header -->
    <div class="view-header">
      <div>
        <h1>Eltern</h1>
        <p>Verwaltung der Elternkontakte</p>
      </div>
      <Button
        :label="isMobile ? '' : 'Hinzufügen'"
        icon="pi pi-plus"
        @click="navigateToCreate"
        severity="primary"
      />
    </div>

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
          :rows="20"
          :total-records="parentsStore.pagination.count"
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

    <!-- Mobile: Card Grid -->
    <div v-else class="cards-grid">
      <ParentCard
        v-for="parent in parentsStore.parents"
        :key="parent.id"
        :parent="parent"
        @edit="navigateToEdit"
        @delete="confirmDelete"
      />
    </div>

    <!-- Mobile Pagination -->
    <div v-if="isMobile && parentsStore.parents.length > 0" class="mobile-pagination">
      <Button
        icon="pi pi-chevron-left"
        outlined
        :disabled="currentPage === 1"
        @click="goToPage(currentPage - 1)"
      />
      <span class="page-info">Seite {{ currentPage }} von {{ totalPages }}</span>
      <Button
        icon="pi pi-chevron-right"
        outlined
        :disabled="currentPage >= totalPages"
        @click="goToPage(currentPage + 1)"
      />
    </div>

    <!-- Delete Confirmation -->
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useParentsStore } from '@/stores/parents'
import type { Parent } from '@/api/members'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import ParentCard from '@/components/parents/ParentCard.vue'

const router = useRouter()
const parentsStore = useParentsStore()
const confirm = useConfirm()
const toast = useToast()

const isMobile = ref(window.innerWidth < 768)
const searchQuery = ref('')
const currentPage = ref(1)

const totalPages = computed(() => {
  return Math.ceil(parentsStore.pagination.count / 20)
})

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
      page: currentPage.value,
      page_size: 20,
      search: searchQuery.value || undefined
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Eltern konnten nicht geladen werden',
      life: 3000
    })
  }
}

let searchTimeout: any
const handleSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    fetchParents()
  }, 500)
}

const onPage = (event: any) => {
  currentPage.value = event.page + 1
  parentsStore.fetchParents({
    page: currentPage.value,
    page_size: event.rows,
    search: searchQuery.value || undefined
  })
}

const goToPage = (page: number) => {
  currentPage.value = page
  fetchParents()
}

const navigateToCreate = () => {
  router.push('/parents/create')
}

const navigateToEdit = (parent: Parent) => {
  router.push(`/parents/${parent.id}/edit`)
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
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Elternteil konnte nicht gelöscht werden',
      life: 3000
    })
  }
}
</script>


