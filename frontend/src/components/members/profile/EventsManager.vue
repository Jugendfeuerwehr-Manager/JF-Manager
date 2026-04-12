<template>
  <div class="events-manager">
    <div class="section-header">
      <Button 
        label="Neuer Eintrag" 
        icon="pi pi-plus" 
        @click="openCreateDialog"
        :disabled="eventsStore.loading"
      />
    </div>

    <!-- Create/Edit Dialog -->
    <Dialog 
      v-model:visible="showDialog" 
      :header="editingEvent ? 'Eintrag bearbeiten' : 'Neuer Eintrag'" 
      :modal="true"
      :style="{ width: '50vw' }"
      :breakpoints="{ '960px': '75vw', '640px': '90vw' }"
    >
      <div class="event-form">
        <div class="field">
          <label for="event-type">Typ *</label>
          <Dropdown 
            id="event-type"
            v-model="eventForm.type"
            :options="eventsStore.eventTypeOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Ereignistyp auswählen"
            :invalid="!!errors.type"
            :loading="eventsStore.loading"
          />
          <small v-if="errors.type" class="p-error">{{ errors.type }}</small>
        </div>

        <div class="field">
          <label for="event-date">Datum *</label>
          <Calendar 
            id="event-date"
            v-model="eventForm.datetime"
            date-format="yy-mm-dd"
            :show-icon="true"
            :max-date="new Date()"
            :invalid="!!errors.datetime"
            update-model-type="replace"
          />
          <small v-if="errors.datetime" class="p-error">{{ errors.datetime }}</small>
        </div>

        <div class="field">
          <label for="event-notes">Bemerkungen</label>
          <Textarea 
            id="event-notes"
            v-model="eventForm.notes"
            rows="4"
            placeholder="Optionale Bemerkungen zum Ereignis"
          />
        </div>
      </div>

      <template #footer>
        <Button 
          label="Abbrechen" 
          icon="pi pi-times" 
          @click="closeDialog"
          severity="secondary"
          :disabled="saving"
        />
        <Button 
          :label="editingEvent ? 'Speichern' : 'Erstellen'" 
          icon="pi pi-check" 
          @click="saveEvent"
          :loading="saving"
        />
      </template>
    </Dialog>

    <!-- Events List -->
    <div v-if="eventsStore.loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <div v-else-if="!sortedEvents.length" class="empty-state">
      <i class="pi pi-calendar"></i>
      <p>Noch keine Einträge vorhanden</p>
      <Button 
        label="Ersten Eintrag erstellen" 
        icon="pi pi-plus" 
        @click="openCreateDialog"
      />
    </div>

    <!-- Events DataView -->
    <DataView 
      v-else 
      :value="sortedEvents" 
      class="events-dataview"
      data-key="id"
    >
      <template #list="slotProps">
        <div v-for="event in slotProps.items" :key="event.id" class="event-item">
          <div class="event-content">
            <div class="event-header">
              <div class="event-date-badge">
                <i class="pi pi-calendar"></i>
                <span>{{ formatDate(event.datetime) }}</span>
              </div>
              <Tag 
                :value="event.event_type?.name || 'Unbekannt'" 
                class="event-type-tag"
              />
            </div>
            
            <div v-if="event.notes" class="event-notes">
              <p>{{ event.notes }}</p>
            </div>
            <div v-else class="event-notes-empty">
              <i class="pi pi-info-circle"></i>
              <span>Keine Bemerkungen</span>
            </div>

            <div class="event-actions">
              <Button 
                icon="pi pi-pencil" 
                text
                rounded
                size="small"
                severity="info"
                @click="openEditDialog(event)"
                v-tooltip.top="'Bearbeiten'"
              />
              <Button 
                icon="pi pi-trash" 
                text
                rounded
                size="small"
                severity="danger"
                @click="confirmDeleteEvent(event)"
                v-tooltip.top="'Löschen'"
              />
            </div>
          </div>
        </div>
      </template>
    </DataView>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useEventsStore } from '@/stores/events'
import type { Event } from '@/types/api'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Calendar from 'primevue/calendar'
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'
import DataView from 'primevue/dataview'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import { getApiErrorMessage } from '@/utils/apiError'

interface Props {
  memberId: number
}

const props = defineProps<Props>()
const toast = useToast()
const confirm = useConfirm()
const eventsStore = useEventsStore()

const saving = ref(false)
const showDialog = ref(false)
const editingEvent = ref<Event | null>(null)

const eventForm = ref({
  type: null as number | null,
  datetime: null as Date | null,
  notes: ''
})

const errors = ref({
  type: '',
  datetime: ''
})

const sortedEvents = computed(() => eventsStore.getEventsByMember(props.memberId))

onMounted(() => {
  loadEvents()
  loadEventTypes()
})

const loadEvents = async () => {
  try {
    await eventsStore.fetchEventsForMember(props.memberId)
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Einträge konnten nicht geladen werden',
      life: 3000
    })
  }
}

const loadEventTypes = async () => {
  try {
    await eventsStore.fetchEventTypes()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Ereignistypen konnten nicht geladen werden',
      life: 3000
    })
  }
}

const openCreateDialog = () => {
  editingEvent.value = null
  eventForm.value = {
    type: null,
    datetime: new Date(),
    notes: ''
  }
  errors.value = { type: '', datetime: '' }
  showDialog.value = true
}

const openEditDialog = (event: Event) => {
  editingEvent.value = event
  eventForm.value = {
    type: event.type,
    datetime: new Date(event.datetime),
    notes: event.notes || ''
  }
  errors.value = { type: '', datetime: '' }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
  editingEvent.value = null
  eventForm.value = { type: null, datetime: null, notes: '' }
  errors.value = { type: '', datetime: '' }
}

const validateForm = (): boolean => {
  errors.value = { type: '', datetime: '' }
  let isValid = true

  if (!eventForm.value.type) {
    errors.value.type = 'Typ ist erforderlich'
    isValid = false
  }

  if (!eventForm.value.datetime) {
    errors.value.datetime = 'Datum ist erforderlich'
    isValid = false
  }

  return isValid
}

const saveEvent = async () => {
  if (!validateForm()) {
    return
  }

  saving.value = true

  try {
    const datetimeStr = eventForm.value.datetime!.toISOString().split('T')[0]
    if (!datetimeStr) {
      throw new Error('Invalid date')
    }

    const data = {
      member: props.memberId,
      type: eventForm.value.type!,
      datetime: datetimeStr,
      notes: eventForm.value.notes
    }

    if (editingEvent.value) {
      await eventsStore.updateEvent(editingEvent.value.id, data)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Eintrag wurde aktualisiert',
        life: 3000
      })
    } else {
      await eventsStore.createEvent(data)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Eintrag wurde erstellt',
        life: 3000
      })
    }

    closeDialog()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: getApiErrorMessage(error, 'Fehler beim Speichern'),
      life: 3000
    })
  } finally {
    saving.value = false
  }
}

const confirmDeleteEvent = (event: Event) => {
  confirm.require({
    message: `Möchten Sie diesen Eintrag wirklich löschen?`,
    header: 'Eintrag löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: () => deleteEvent(event.id)
  })
}

const deleteEvent = async (id: number) => {
  try {
    await eventsStore.deleteEvent(id)
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: 'Eintrag wurde gelöscht',
      life: 3000
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Eintrag konnte nicht gelöscht werden',
      life: 3000
    })
  }
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}
</script>

<style scoped>
.events-manager {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.event-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 500;
}

.p-error {
  color: var(--red-500);
  font-size: 0.875rem;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 3rem;
  text-align: center;
  border: 2px dashed var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-50);
}

.empty-state i {
  font-size: 3rem;
  color: var(--text-color-secondary);
}

.empty-state p {
  margin: 0;
  color: var(--text-color-secondary);
}

/* Events DataView */
.events-dataview {
  background: transparent;
}

.events-dataview :deep(.p-dataview-content) {
  background: transparent;
}

.event-item {
  padding: 1rem;
  margin-bottom: 1rem;
  border-left: 4px solid var(--primary-color);
  border-radius: var(--border-radius);
  background: var(--surface-card);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}



.event-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.event-date-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--surface-100);
  border-radius: var(--border-radius);
  font-weight: 500;
  font-size: 0.875rem;
}

.event-date-badge i {
  color: var(--primary-color);
}

.event-type-tag {
  font-size: 0.875rem;
}

.event-notes {
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: var(--border-radius);
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}

.event-notes p {
  margin: 0;
  color: var(--text-color);
}

.event-notes-empty {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  color: var(--text-color-secondary);
  font-style: italic;
  font-size: 0.875rem;
}

.event-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-border);
}

.event-actions :deep(button) {
  position: relative !important;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }

  .event-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .event-date-badge {
    max-width: 200px;
  }
}
</style>
