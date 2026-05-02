<template>
  <div class="departments-panel">
    <div class="flex gap-3 align-items-start">
      <!-- Left: Department List -->
      <div class="flex-1 min-w-0">
        <Card>
          <template #header>
            <div class="card-header">
              <span class="font-semibold">Abteilungen</span>
              <Button label="Neue Abteilung" icon="pi pi-plus" size="small" @click="openCreateDialog" />
            </div>
          </template>
          <template #content>
            <DataTable
              :value="departmentsStore.departments"
              :loading="departmentsStore.loading"
              selection-mode="single"
              v-model:selection="selectedDept"
              striped-rows
              size="small"
              @row-select="onDeptSelect"
            >
              <Column field="code" header="Kürzel" :style="{ width: '7rem' }" />
              <Column field="name" header="Name" />
              <Column header="Farbe" :style="{ width: '6rem' }">
                <template #body="{ data }">
                  <span class="dept-color-dot" :style="{ backgroundColor: data.color }" :title="data.color" />
                </template>
              </Column>
              <Column field="address" header="Adresse" class="hidden md:table-cell" />
              <Column header="Status" :style="{ width: '7rem' }">
                <template #body="{ data }">
                  <Tag
                    :value="data.is_active ? 'Aktiv' : 'Inaktiv'"
                    :severity="data.is_active ? 'success' : 'secondary'"
                  />
                </template>
              </Column>
              <Column header="Aktionen" :style="{ width: '9rem' }">
                <template #body="{ data }">
                  <div class="flex gap-1">
                    <Button
                      icon="pi pi-users"
                      size="small"
                      text
                      rounded
                      v-tooltip.top="'Benutzer verwalten'"
                      @click="selectDeptForRoles(data)"
                    />
                    <Button icon="pi pi-pencil" size="small" text rounded @click="openEditDialog(data)" />
                    <Button
                      icon="pi pi-trash"
                      size="small"
                      text
                      rounded
                      severity="danger"
                      @click="confirmDelete(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </template>
        </Card>
      </div>

      <!-- Right: User roles for selected department -->
      <div v-if="selectedDept" class="dept-roles-panel" style="min-width: 340px; width: 380px">
        <Card>
          <template #header>
            <div class="card-header">
              <span class="font-semibold">{{ selectedDept.name }}: Benutzer</span>
              <Button
                label="Hinzufügen"
                icon="pi pi-user-plus"
                size="small"
                @click="openAddRoleDialog"
              />
            </div>
          </template>
          <template #content>
            <div v-if="rolesLoading" class="flex justify-content-center py-3">
              <ProgressSpinner style="width: 32px; height: 32px" />
            </div>
            <div v-else-if="departmentRoles.length === 0" class="text-color-secondary text-sm py-2">
              Keine Benutzer zugewiesen.
            </div>
            <div v-else class="flex flex-column gap-2">
              <div
                v-for="roleEntry in departmentRoles"
                :key="roleEntry.id"
                class="flex align-items-center justify-content-between p-2 border-round surface-100"
              >
                <div class="flex flex-column gap-1 min-w-0">
                  <span class="font-medium text-sm">{{ roleEntry.username }}</span>
                  <div v-if="roleEntry.groups.length > 0" class="flex flex-wrap gap-1">
                    <Tag
                      v-for="g in roleEntry.groups"
                      :key="g.id"
                      :value="g.name"
                      severity="info"
                      style="font-size: 0.7rem"
                    />
                  </div>
                  <span v-else class="text-color-secondary text-xs">Keine Gruppen</span>
                </div>
                <div class="flex gap-1 ml-2 flex-shrink-0">
                  <Button
                    icon="pi pi-pencil"
                    size="small"
                    text
                    rounded
                    v-tooltip.top="'Gruppen bearbeiten'"
                    @click="openEditRoleDialog(roleEntry)"
                  />
                  <Button
                    icon="pi pi-times"
                    size="small"
                    text
                    rounded
                    severity="danger"
                    v-tooltip.top="'Entfernen'"
                    @click="removeRole(roleEntry)"
                  />
                </div>
              </div>
            </div>
          </template>
        </Card>
      </div>
    </div>

    <!-- Create/Edit Department Dialog -->
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
          <label for="deptColor">Farbe</label>
          <div class="flex align-items-center gap-2">
            <input id="deptColor" v-model="form.color" type="color" class="dept-color-input" />
            <InputText v-model="form.color" class="w-full" maxlength="7" placeholder="#2563EB" />
          </div>
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

    <!-- Add/Edit user-role Dialog -->
    <Dialog
      v-model:visible="roleDialogVisible"
      :header="editingRole ? 'Gruppen bearbeiten' : 'Benutzer hinzufügen'"
      modal
      :style="{ width: '420px' }"
      @hide="resetRoleForm"
    >
      <div class="flex flex-column gap-3">
        <div v-if="!editingRole" class="field">
          <label for="roleUser">Benutzer *</label>
          <Select
            id="roleUser"
            v-model="roleForm.user"
            :options="availableUsers"
            option-label="full_name"
            option-value="id"
            placeholder="Benutzer auswählen"
            filter
            class="w-full"
          />
        </div>
        <div v-else class="text-sm font-medium mb-1">
          Benutzer: {{ editingRole.username }}
        </div>
        <div class="field">
          <label for="roleGroups">Gruppen</label>
          <MultiSelect
            id="roleGroups"
            v-model="roleForm.group_ids"
            :options="availableGroups"
            option-label="name"
            option-value="id"
            placeholder="Gruppen auswählen"
            filter
            class="w-full"
            display="chip"
          />
          <small class="text-color-secondary">
            Berechtigungen aus den gewählten Gruppen gelten in dieser Abteilung
          </small>
        </div>
        <div class="flex justify-content-end gap-2">
          <Button label="Abbrechen" severity="secondary" @click="roleDialogVisible = false" />
          <Button
            :label="editingRole ? 'Speichern' : 'Hinzufügen'"
            :disabled="!editingRole && !roleForm.user"
            :loading="roleSaving"
            @click="saveRole"
          />
        </div>
      </div>
    </Dialog>

    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useDepartmentsStore } from '@/stores/departments'
import { useAdminStore } from '@/stores/admin'
import { departmentsApi, departmentRolesApi } from '@/api/departments'
import type { Department, UserDepartmentRole } from '@/types/departments'
import { adminGroupsApi } from '@/api/admin'
import type { AuthGroup } from '@/types/admin'
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
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import ProgressSpinner from 'primevue/progressspinner'

const toast = useToast()
const confirm = useConfirm()
const departmentsStore = useDepartmentsStore()
const adminStore = useAdminStore()

// ── Department CRUD state ────────────────────────────────────────────────────

const dialogVisible = ref(false)
const editingDept = ref<Department | null>(null)
const saving = ref(false)

const form = reactive({
  name: '',
  code: '',
  color: '#2563EB',
  description: '',
  address: '',
  phone: '',
  is_active: true,
})

function resetForm() {
  form.name = ''
  form.code = ''
  form.color = '#2563EB'
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
  form.color = dept.color
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
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Abteilung konnte nicht gespeichert werden',
      life: 3000,
    })
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
    if (selectedDept.value?.id === dept.id) {
      selectedDept.value = null
    }
    await departmentsStore.fetchDepartments()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Abteilung konnte nicht gelöscht werden',
      life: 3000,
    })
  }
}

// ── User-Department Role state ───────────────────────────────────────────────

const selectedDept = ref<Department | null>(null)
const departmentRoles = ref<UserDepartmentRole[]>([])
const rolesLoading = ref(false)
const roleDialogVisible = ref(false)
const roleSaving = ref(false)
const editingRole = ref<UserDepartmentRole | null>(null)
const availableGroups = ref<AuthGroup[]>([])

const roleForm = reactive<{ user: number | null; group_ids: number[] }>({
  user: null,
  group_ids: [],
})

/** Users not yet assigned to the selected department */
const availableUsers = computed(() => {
  const assignedUserIds = new Set(departmentRoles.value.map((r) => r.user))
  return adminStore.users.filter((u) => !assignedUserIds.has(u.id))
})

async function loadRoles(deptId: number) {
  rolesLoading.value = true
  try {
    const response = await departmentRolesApi.list({ department: deptId })
    departmentRoles.value = response.data.results
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Benutzer konnten nicht geladen werden', life: 3000 })
  } finally {
    rolesLoading.value = false
  }
}

function selectDeptForRoles(dept: Department) {
  selectedDept.value = dept
  loadRoles(dept.id)
}

function onDeptSelect(event: { data: Department }) {
  loadRoles(event.data.id)
}

function resetRoleForm() {
  roleForm.user = null
  roleForm.group_ids = []
  editingRole.value = null
}

function openAddRoleDialog() {
  resetRoleForm()
  roleDialogVisible.value = true
}

function openEditRoleDialog(roleEntry: UserDepartmentRole) {
  editingRole.value = roleEntry
  roleForm.user = roleEntry.user
  roleForm.group_ids = roleEntry.groups.map((g) => g.id)
  roleDialogVisible.value = true
}

async function saveRole() {
  if (!selectedDept.value) return
  roleSaving.value = true
  try {
    if (editingRole.value) {
      await departmentRolesApi.update(editingRole.value.id, { group_ids: roleForm.group_ids })
      toast.add({ severity: 'success', summary: 'Gespeichert', detail: 'Gruppen wurden aktualisiert', life: 3000 })
    } else {
      if (!roleForm.user) return
      await departmentRolesApi.create({
        user: roleForm.user,
        department: selectedDept.value.id,
        group_ids: roleForm.group_ids,
      })
      toast.add({ severity: 'success', summary: 'Hinzugefügt', detail: 'Benutzer wurde hinzugefügt', life: 3000 })
    }
    roleDialogVisible.value = false
    await loadRoles(selectedDept.value.id)
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Änderungen konnten nicht gespeichert werden',
      life: 3000,
    })
  } finally {
    roleSaving.value = false
  }
}

async function removeRole(roleEntry: UserDepartmentRole) {
  try {
    await departmentRolesApi.delete(roleEntry.id)
    departmentRoles.value = departmentRoles.value.filter((r) => r.id !== roleEntry.id)
    toast.add({ severity: 'success', summary: 'Entfernt', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Benutzer konnte nicht entfernt werden', life: 3000 })
  }
}

onMounted(async () => {
  await Promise.all([
    departmentsStore.fetchDepartments(),
    adminStore.fetchUsers({ limit: 1000 }),
    adminGroupsApi.list({ limit: 200 }).then((r) => {
      availableGroups.value = r.data.results
    }),
  ])
})
</script>

<style scoped>
.departments-panel {
  padding: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-border);
}

.dept-roles-panel {
  flex-shrink: 0;
}

.dept-color-dot {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  display: inline-block;
  border: 1px solid var(--surface-border);
}

.dept-color-input {
  width: 2.5rem;
  height: 2.25rem;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 0;
  background: transparent;
}

@media (max-width: 768px) {
  .departments-panel > .flex {
    flex-direction: column;
  }

  .dept-roles-panel {
    width: 100% !important;
    min-width: unset !important;
  }
}
</style>
