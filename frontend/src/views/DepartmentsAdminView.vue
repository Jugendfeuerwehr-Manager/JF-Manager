<template>
  <div class="admin-view p-3 md:p-4">
    <div class="mb-4">
      <h1 class="text-3xl font-bold m-0">Abteilungsverwaltung</h1>
      <p class="text-color-secondary mt-1 mb-0">Abteilungen anlegen, bearbeiten und Benutzer zuweisen</p>
    </div>

    <!-- Departments list -->
    <Card>
      <template #header>
        <div class="card-header">
          <span class="font-semibold">Abteilungen</span>
          <Button
            label="Neue Abteilung"
            icon="pi pi-plus"
            size="small"
            @click="openCreateDialog"
          />
        </div>
      </template>
      <template #content>
        <DataTable
          :value="departmentsStore.departments"
          :loading="departmentsStore.loading"
          striped-rows
          size="small"
        >
          <Column field="code" header="Kürzel" :style="{ width: '8rem' }" />
          <Column field="name" header="Name" />
          <Column field="address" header="Adresse" />
          <Column field="phone" header="Telefon" />
          <Column header="Status" :style="{ width: '8rem' }">
            <template #body="{ data }">
              <Tag :value="data.is_active ? 'Aktiv' : 'Inaktiv'" :severity="data.is_active ? 'success' : 'secondary'" />
            </template>
          </Column>
          <Column header="Aktionen" :style="{ width: '10rem' }">
            <template #body="{ data }">
              <div class="flex gap-2">
                <Button icon="pi pi-pencil" size="small" text rounded @click="openEditDialog(data)" />
                <Button icon="pi pi-trash" size="small" text rounded severity="danger" @click="confirmDelete(data)" />
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Create/Edit dialog -->
    <Dialog
      v-model:visible="dialogVisible"
      :header="editingDept ? 'Abteilung bearbeiten' : 'Neue Abteilung'"
      modal
      :style="{ width: '480px' }"
      @hide="resetForm"
    >
      <form @submit.prevent="handleSave" class="flex flex-column gap-3">
        <div class="field">
          <label for="deptName">Name *</label>
          <InputText id="deptName" v-model="form.name" class="w-full" required />
        </div>
        <div class="field">
          <label for="deptCode">Kürzel *</label>
          <InputText id="deptCode" v-model="form.code" class="w-full" required maxlength="10" />
          <small class="text-color-secondary">Eindeutiges Kürzel (z.B. "NORD", "SUED")</small>
        </div>
        <div class="field">
          <label for="deptDesc">Beschreibung</label>
          <Textarea id="deptDesc" v-model="form.description" class="w-full" rows="2" />
        </div>
        <div class="field">
          <label for="deptAddress">Adresse</label>
          <InputText id="deptAddress" v-model="form.address" class="w-full" />
        </div>
        <div class="field">
          <label for="deptPhone">Telefon</label>
          <InputText id="deptPhone" v-model="form.phone" class="w-full" />
        </div>
        <div class="field flex align-items-center gap-2">
          <Checkbox v-model="form.is_active" input-id="deptActive" :binary="true" />
          <label for="deptActive">Aktiv</label>
        </div>
        <div class="flex justify-content-end gap-2 mt-2">
          <Button label="Abbrechen" severity="secondary" @click="dialogVisible = false" />
          <Button label="Speichern" type="submit" :loading="saving" />
        </div>
      </form>
    </Dialog>

    <!-- Confirm delete -->
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useDepartmentsStore } from '@/stores/departments'
import { departmentsApi } from '@/api/departments'
import type { Department } from '@/types/departments'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import ConfirmDialog from 'primevue/confirmdialog'

const toast = useToast()
const confirm = useConfirm()
const departmentsStore = useDepartmentsStore()

const dialogVisible = ref(false)
const editingDept = ref<Department | null>(null)
const saving = ref(false)

const form = reactive({
  name: '',
  code: '',
  description: '',
  address: '',
  phone: '',
  is_active: true,
})

function resetForm() {
  form.name = ''
  form.code = ''
  form.description = ''
  form.address = ''
  form.phone = ''
  form.is_active = true
  editingDept.value = null
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(dept: Department) {
  editingDept.value = dept
  form.name = dept.name
  form.code = dept.code
  form.description = dept.description
  form.address = dept.address
  form.phone = dept.phone
  form.is_active = dept.is_active
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingDept.value) {
      await departmentsApi.update(editingDept.value.id, { ...form })
    } else {
      await departmentsApi.create({ ...form })
    }
    toast.add({ severity: 'success', summary: 'Gespeichert', detail: 'Abteilung wurde gespeichert', life: 3000 })
    dialogVisible.value = false
    await departmentsStore.fetchDepartments()
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Abteilung konnte nicht gespeichert werden', life: 3000 })
  } finally {
    saving.value = false
  }
}

function confirmDelete(dept: Department) {
  confirm.require({
    message: `Abteilung "${dept.name}" wirklich löschen?`,
    header: 'Bestätigung',
    icon: 'pi pi-trash',
    accept: () => deleteDept(dept),
  })
}

async function deleteDept(dept: Department) {
  try {
    await departmentsApi.delete(dept.id)
    toast.add({ severity: 'success', summary: 'Gelöscht', detail: 'Abteilung wurde gelöscht', life: 3000 })
    await departmentsStore.fetchDepartments()
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Abteilung konnte nicht gelöscht werden', life: 3000 })
  }
}

onMounted(() => {
  departmentsStore.fetchDepartments()
})
</script>

<style scoped>
.admin-view {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem 0;
}
</style>
