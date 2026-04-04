<template>
  <SettingsCategoryCard
    title="Eintragstypen"
    description="Verwalten Sie die verfügbaren Typen für Mitgliedereinträge"
    icon="pi pi-bookmark"
  >
    <div class="event-types-manager">
      <!-- Add new type form -->
      <div v-if="showAddForm" class="add-form">
        <div class="add-form-row">
          <InputText
            v-model="newName"
            placeholder="Typbezeichnung"
            class="flex-1"
            :class="{ 'p-invalid': addError }"
            @keyup.enter="saveNew"
          />
          <Button
            icon="pi pi-check"
            severity="success"
            :loading="saving"
            @click="saveNew"
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

      <!-- List -->
      <div v-if="loading" class="flex justify-content-center p-3">
        <ProgressSpinner style="width: 2rem; height: 2rem" />
      </div>

      <div v-else-if="!eventTypes.length && !showAddForm" class="empty-hint">
        <i class="pi pi-info-circle"></i>
        <span>Noch keine Eintragstypen vorhanden</span>
      </div>

      <div v-else class="types-list">
        <div
          v-for="et in eventTypes"
          :key="et.id"
          class="type-row"
        >
          <template v-if="editingId !== et.id">
            <i class="pi pi-bookmark type-icon"></i>
            <span class="type-name">{{ et.name }}</span>
            <div class="type-actions">
              <Button
                icon="pi pi-pencil"
                text
                rounded
                size="small"
                severity="info"
                v-tooltip.top="'Bearbeiten'"
                @click="startEdit(et)"
              />
              <Button
                icon="pi pi-trash"
                text
                rounded
                size="small"
                severity="danger"
                v-tooltip.top="'Löschen'"
                @click="confirmDelete(et)"
              />
            </div>
          </template>

          <template v-else>
            <div class="add-form-row flex-1">
              <InputText
                v-model="editName"
                class="flex-1"
                @keyup.enter="saveEdit(et.id)"
              />
              <Button
                icon="pi pi-check"
                severity="success"
                size="small"
                :loading="saving"
                @click="saveEdit(et.id)"
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
          label="Eintragstyp hinzufügen"
          icon="pi pi-plus"
          severity="secondary"
          :disabled="!canEdit"
          @click="showAddForm = true"
        />
      </div>
    </div>

    <ConfirmDialog />
  </SettingsCategoryCard>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import SettingsCategoryCard from '../atoms/SettingsCategoryCard.vue'
import { eventTypesApi } from '@/api/members'
import type { EventType } from '@/types/api'

interface Props {
  canEdit: boolean
}
const props = defineProps<Props>()

const confirm = useConfirm()
const toast = useToast()

const eventTypes = ref<EventType[]>([])
const loading = ref(false)
const saving = ref(false)
const showAddForm = ref(false)
const addError = ref('')
const editingId = ref<number | null>(null)
const newName = ref('')
const editName = ref('')

async function loadEventTypes() {
  loading.value = true
  try {
    const response = await eventTypesApi.list()
    eventTypes.value = response.data.results || []
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Eintragstypen konnten nicht geladen werden', life: 3000 })
  } finally {
    loading.value = false
  }
}

async function saveNew() {
  addError.value = ''
  if (!newName.value.trim()) {
    addError.value = 'Bezeichnung ist erforderlich'
    return
  }
  saving.value = true
  try {
    const response = await eventTypesApi.create({ name: newName.value.trim() })
    eventTypes.value.push(response.data)
    cancelAdd()
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'Eintragstyp erstellt', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Fehler beim Erstellen', life: 3000 })
  } finally {
    saving.value = false
  }
}

function cancelAdd() {
  showAddForm.value = false
  addError.value = ''
  newName.value = ''
}

function startEdit(et: EventType) {
  editingId.value = et.id
  editName.value = et.name
}

function cancelEdit() {
  editingId.value = null
}

async function saveEdit(id: number) {
  saving.value = true
  try {
    const response = await eventTypesApi.update(id, { name: editName.value.trim() })
    const idx = eventTypes.value.findIndex(t => t.id === id)
    if (idx !== -1) eventTypes.value[idx] = response.data
    cancelEdit()
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'Eintragstyp gespeichert', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Fehler beim Speichern', life: 3000 })
  } finally {
    saving.value = false
  }
}

function confirmDelete(et: EventType) {
  confirm.require({
    message: `Eintragstyp "${et.name}" wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: () => deleteEventType(et.id)
  })
}

async function deleteEventType(id: number) {
  try {
    await eventTypesApi.delete(id)
    eventTypes.value = eventTypes.value.filter(t => t.id !== id)
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'Eintragstyp gelöscht', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Fehler beim Löschen', life: 3000 })
  }
}

onMounted(loadEventTypes)
</script>

<style scoped>
.types-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.type-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--p-border-radius-md);
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
}

.type-icon {
  color: var(--p-text-muted-color);
  flex-shrink: 0;
}

.type-name {
  flex: 1;
  font-weight: 500;
}

.type-actions {
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
}

.empty-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-muted-color);
  padding: 0.5rem 0;
}
</style>
