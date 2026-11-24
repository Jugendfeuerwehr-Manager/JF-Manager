<template>
  <SettingsCategoryCard
    title="Mitgliedstatus"
    description="Stufen der Mitgliedschaft. Die Kategorie bestimmt, wie eine Stufe in der Jahresmeldung zählt. Reihenfolge per Ziehen oder mit den Pfeilen ändern."
    icon="pi pi-tag"
  >
    <div class="statuses-manager">
      <!-- Add new status form -->
      <div v-if="showAddForm" class="add-form">
        <div class="add-form-row">
          <InputText
            v-model="newStatus.name"
            placeholder="Status-Name"
            class="flex-1"
            :class="{ 'p-invalid': addError }"
            @keyup.enter="saveNewStatus"
          />
          <Select
            v-model="newStatus.category"
            :options="categoryOptions"
            option-label="label"
            option-value="value"
            aria-label="Kategorie"
          />
          <ColorPicker v-model="newStatus.color" format="hex" />
          <div
            class="color-preview"
            :style="{ background: '#' + newStatus.color }"
          />
          <Button
            icon="pi pi-check"
            severity="success"
            :loading="saving"
            @click="saveNewStatus"
          />
          <Button
            icon="pi pi-times"
            severity="secondary"
            text
            @click="cancelAdd"
          />
        </div>
        <small v-if="addError" class="p-error">{{ addError }}</small>
      </div>

      <!-- Statuses list -->
      <div v-if="loading" class="flex justify-content-center p-3">
        <ProgressSpinner style="width: 2rem; height: 2rem" />
      </div>

      <div v-else-if="!statuses.length && !showAddForm" class="empty-hint">
        <i class="pi pi-info-circle"></i>
        <span>Noch keine Status vorhanden</span>
      </div>

      <div v-else class="statuses-list">
        <div
          v-for="(status, index) in statuses"
          :key="status.id"
          class="status-row"
          :class="{ 'status-row--drop': dropIndex === index }"
          :draggable="canEdit && editingId === null"
          @dragstart="dragIndex = index"
          @dragover.prevent="dropIndex = index"
          @dragleave="dropIndex = null"
          @drop.prevent="dropAt(index)"
          @dragend="dragIndex = dropIndex = null"
        >
          <template v-if="editingId !== status.id">
            <i v-if="canEdit" class="pi pi-bars status-handle" aria-hidden="true" />
            <div class="status-color-dot" :style="{ background: status.color }" />
            <span class="status-name">{{ status.name }}</span>
            <span class="status-category">{{ STATUS_CATEGORY_LABELS[status.category] }}</span>
            <span v-if="status.department === null" class="status-scope">zentral</span>
            <div class="status-actions">
              <Button
                icon="pi pi-arrow-up"
                text
                rounded
                size="small"
                severity="secondary"
                :aria-label="`${status.name} nach oben`"
                :disabled="!canEdit || index === 0"
                @click="move(index, index - 1)"
              />
              <Button
                icon="pi pi-arrow-down"
                text
                rounded
                size="small"
                severity="secondary"
                :aria-label="`${status.name} nach unten`"
                :disabled="!canEdit || index === statuses.length - 1"
                @click="move(index, index + 1)"
              />
              <Button
                icon="pi pi-pencil"
                text
                rounded
                size="small"
                severity="info"
                v-tooltip.top="'Bearbeiten'"
                @click="startEdit(status)"
              />
              <Button
                icon="pi pi-trash"
                text
                rounded
                size="small"
                severity="danger"
                v-tooltip.top="'Löschen'"
                @click="confirmDelete(status)"
              />
            </div>
          </template>

          <template v-else>
            <div class="add-form-row flex-1">
              <InputText
                v-model="editForm.name"
                class="flex-1"
                @keyup.enter="saveEdit(status.id)"
              />
              <Select
                v-model="editForm.category"
                :options="categoryOptions"
                option-label="label"
                option-value="value"
                aria-label="Kategorie"
              />
              <ColorPicker v-model="editForm.color" format="hex" />
              <Button
                icon="pi pi-check"
                severity="success"
                size="small"
                :loading="saving"
                @click="saveEdit(status.id)"
              />
              <Button
                icon="pi pi-times"
                severity="secondary"
                text
                size="small"
                @click="cancelEdit"
              />
            </div>
          </template>
        </div>
      </div>

      <!-- Add button -->
      <div v-if="!showAddForm" class="mt-3">
        <Button
          label="Status hinzufügen"
          icon="pi pi-plus"
          severity="secondary"
          :disabled="!canEdit"
          @click="showAddForm = true"
        />
      </div>
    </div>

  </SettingsCategoryCard>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ColorPicker from 'primevue/colorpicker'
import ProgressSpinner from 'primevue/progressspinner'
import Select from 'primevue/select'
import SettingsCategoryCard from '../atoms/SettingsCategoryCard.vue'
import { statusesApi } from '@/api/members'
import type { Status, StatusCategory } from '@/types/members'
import { STATUS_CATEGORY_LABELS } from '@/types/membership'
import { useDepartmentsStore } from '@/stores/departments'

interface Props {
  canEdit: boolean
}
defineProps<Props>()

const confirm = useConfirm()
const toast = useToast()

const statuses = ref<Status[]>([])
const loading = ref(false)
const saving = ref(false)
const showAddForm = ref(false)
const addError = ref('')
const editingId = ref<number | null>(null)

const departmentsStore = useDepartmentsStore()
const categoryOptions = Object.entries(STATUS_CATEGORY_LABELS).map(([value, label]) => ({ value, label }))
const dragIndex = ref<number | null>(null)
const dropIndex = ref<number | null>(null)

const newStatus = ref<{ name: string; color: string; category: StatusCategory }>({ name: '', color: 'ef4444', category: 'active' })
const editForm = ref<{ name: string; color: string; category: StatusCategory }>({ name: '', color: 'ef4444', category: 'active' })

async function loadStatuses() {
  loading.value = true
  try {
    const response = await statusesApi.list()
    statuses.value = response.data.results || []
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Status konnten nicht geladen werden', life: 3000 })
  } finally {
    loading.value = false
  }
}

async function saveNewStatus() {
  addError.value = ''
  if (!newStatus.value.name.trim()) {
    addError.value = 'Name ist erforderlich'
    return
  }
  saving.value = true
  try {
    // New stages belong to the selected department; with "all departments" they are central.
    const response = await statusesApi.create({
      name: newStatus.value.name.trim(),
      color: '#' + newStatus.value.color,
      category: newStatus.value.category,
      department: departmentsStore.activeDepartmentId,
      sort_order: statuses.value.length
    })
    statuses.value.push(response.data)
    cancelAdd()
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'Status erstellt', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Fehler beim Erstellen des Status', life: 3000 })
  } finally {
    saving.value = false
  }
}

function cancelAdd() {
  showAddForm.value = false
  addError.value = ''
  newStatus.value = { name: '', color: 'ef4444', category: 'active' }
}

function startEdit(status: Status) {
  editingId.value = status.id
  editForm.value = {
    name: status.name,
    color: status.color.replace('#', ''),
    category: status.category
  }
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit(id: number) {
  saving.value = true
  try {
    const response = await statusesApi.update(id, {
      name: editForm.value.name.trim(),
      color: '#' + editForm.value.color,
      category: editForm.value.category
    })
    const idx = statuses.value.findIndex(s => s.id === id)
    if (idx !== -1) statuses.value[idx] = response.data
    cancelEdit()
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'Status gespeichert', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Fehler beim Speichern', life: 3000 })
  } finally {
    saving.value = false
  }
}

function confirmDelete(status: Status) {
  confirm.require({
    message: `Status "${status.name}" wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: () => deleteStatus(status.id)
  })
}

async function deleteStatus(id: number) {
  try {
    await statusesApi.delete(id)
    statuses.value = statuses.value.filter(s => s.id !== id)
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'Status gelöscht', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Fehler beim Löschen', life: 3000 })
  }
}

function dropAt(index: number) {
  const from = dragIndex.value
  dragIndex.value = dropIndex.value = null
  if (from === null || from === index) return
  move(from, index)
}

async function move(from: number, to: number) {
  if (to < 0 || to >= statuses.value.length) return
  const previous = [...statuses.value]
  const reordered = [...statuses.value]
  const [moved] = reordered.splice(from, 1)
  if (!moved) return
  reordered.splice(to, 0, moved)
  statuses.value = reordered
  const changed = reordered.filter((status, position) => status.sort_order !== position)
  try {
    await Promise.all(changed.map((status) => statusesApi.update(status.id, { sort_order: reordered.indexOf(status) })))
    statuses.value = reordered.map((status, position) => ({ ...status, sort_order: position }))
  } catch {
    statuses.value = previous
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Reihenfolge konnte nicht gespeichert werden', life: 3000 })
  }
}

onMounted(loadStatuses)
</script>

<style scoped>
.statuses-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--p-border-radius-md);
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
}

.status-row[draggable='true'] {
  cursor: grab;
}

.status-row--drop {
  border-color: var(--p-primary-color);
}

.status-handle {
  color: var(--p-text-muted-color);
}

.status-category,
.status-scope {
  font-size: 0.8125rem;
  color: var(--p-text-muted-color);
}

.status-scope {
  padding: 0 0.4rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 999px;
}

.status-color-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-name {
  flex: 1;
  font-weight: 500;
}

.status-actions {
  display: flex;
  gap: 0.25rem;
  margin-left: auto;
}

.add-form {
  margin-bottom: 0.75rem;
}

.add-form-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.color-preview {
  width: 28px;
  height: 28px;
  border-radius: var(--p-border-radius-sm);
  border: 1px solid var(--p-content-border-color);
  flex-shrink: 0;
}

.empty-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
  padding: 0.5rem 0;
}
</style>
