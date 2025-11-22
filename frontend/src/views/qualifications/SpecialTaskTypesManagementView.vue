<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQualificationsStore } from '@/stores/qualifications'
import type { SpecialTaskType } from '@/types/qualifications'
import SpecialTaskTypeForm from '@/components/qualifications/organisms/SpecialTaskTypeForm.vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'

const router = useRouter()
const qualificationsStore = useQualificationsStore()
const toast = useToast()
const confirm = useConfirm()

const showForm = ref(false)
const editingType = ref<SpecialTaskType | null>(null)

onMounted(async () => {
  await qualificationsStore.fetchSpecialTaskTypes()
})

const handleCreate = () => {
  editingType.value = null
  showForm.value = true
}

const handleEdit = (type: SpecialTaskType) => {
  editingType.value = type
  showForm.value = true
}

const handleDelete = (type: SpecialTaskType) => {
  confirm.require({
    message: `Möchten Sie den Aufgabentyp "${type.name}" wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      try {
        await qualificationsStore.deleteSpecialTaskType(type.id)
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Aufgabentyp erfolgreich gelöscht',
          life: 3000
        })
        await qualificationsStore.fetchSpecialTaskTypes(true)
      } catch (error: any) {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: error.message || 'Fehler beim Löschen',
          life: 3000
        })
      }
    }
  })
}

const handleFormSuccess = async () => {
  showForm.value = false
  editingType.value = null
  toast.add({
    severity: 'success',
    summary: 'Erfolg',
    detail: editingType.value ? 'Aufgabentyp aktualisiert' : 'Aufgabentyp erstellt',
    life: 3000
  })
  await qualificationsStore.fetchSpecialTaskTypes(true)
}

const handleFormCancel = () => {
  showForm.value = false
  editingType.value = null
}
</script>

<template>
  <div class="p-4">
    
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">Sonderaufgaben-Typen verwalten</h1>
      <div class="flex gap-2">
        <Button
          label="Zurück"
          icon="pi pi-arrow-left"
          severity="secondary"
          @click="router.push('/qualifications')"
        />
        <Button
          label="Neuer Typ"
          icon="pi pi-plus"
          @click="handleCreate"
        />
      </div>
    </div>

    <Card>
      <template #content>
        <div v-if="qualificationsStore.loadingTypes" class="flex justify-center py-8">
          <ProgressSpinner />
        </div>

        <DataTable
          v-else
          :value="qualificationsStore.specialTaskTypes"
          :paginator="true"
          :rows="10"
          :rowsPerPageOptions="[10, 25, 50]"
          responsiveLayout="scroll"
        >
          <Column field="name" header="Name" sortable />
          <Column field="description" header="Beschreibung">
            <template #body="{ data }">
              {{ data.description || '-' }}
            </template>
          </Column>
          <Column header="Aktionen">
            <template #body="{ data }">
              <div class="flex gap-2">
                <Button
                  icon="pi pi-pencil"
                  severity="info"
                  size="small"
                  @click="handleEdit(data)"
                />
                <Button
                  icon="pi pi-trash"
                  severity="danger"
                  size="small"
                  @click="handleDelete(data)"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Form Dialog -->
    <Dialog
      v-model:visible="showForm"
      :header="editingType ? 'Aufgabentyp bearbeiten' : 'Neuer Aufgabentyp'"
      :modal="true"
      :style="{ width: '50vw' }"
      :breakpoints="{ '960px': '75vw', '640px': '95vw' }"
    >
      <SpecialTaskTypeForm
        :typeId="editingType?.id"
        :initialData="editingType || undefined"
        @success="handleFormSuccess"
        @cancel="handleFormCancel"
      />
    </Dialog>
  </div>
</template>
