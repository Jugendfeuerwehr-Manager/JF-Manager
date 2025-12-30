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

    <!-- Mobile: Responsive List -->
    <ResponsiveList
      v-else
      :items="parentsStore.parents"
      :loading="parentsStore.loading"
      :rows="20"
      :paginator="parentsStore.pagination.count > 20"
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
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import ProgressSpinner from 'primevue/progressspinner'
import ResponsiveList from '@/components/common/ResponsiveList.vue'
import ParentCard from '@/components/parents/ParentCard.vue'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'

const router = useRouter()
const parentsStore = useParentsStore()
const confirm = useConfirm()
const toast = useToast()

const isMobile = ref(window.innerWidth < 768)
const searchQuery = ref('')
const currentPage = ref(1)

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


