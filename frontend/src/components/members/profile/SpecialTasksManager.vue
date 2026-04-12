<template>
  <div class="specialtasks-manager">
    <!-- Header with Add Button -->
    <div class="section-header">
      <h3>
        <i class="pi pi-star"></i>
        Sonderaufgaben
      </h3>
      <Button
        label="Sonderaufgabe hinzufügen"
        icon="pi pi-plus"
        size="small"
        @click="showCreateDialog = true"
      />
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner style="width: 50px; height: 50px" />
    </div>

    <!-- Empty State -->
    <div v-else-if="!hasSpecialTasks" class="empty-state">
      <i class="pi pi-star" style="font-size: 3rem; color: var(--text-color-secondary)"></i>
      <p>Noch keine Sonderaufgaben vorhanden</p>
      <Button
        label="Erste Sonderaufgabe hinzufügen"
        icon="pi pi-plus"
        @click="showCreateDialog = true"
      />
    </div>

    <!-- Special Tasks TreeTable -->
    <div v-else class="specialtasks-treetable">
      <DataTable
        :value="memberSpecialTasks"
        :expandedRows="expandedRows"
        @rowExpand="onRowExpand"
        @rowCollapse="onRowCollapse"
        dataKey="id"
        responsiveLayout="scroll"
        stripedRows
      >
        <!-- Expander Column -->
        <Column :expander="true" headerStyle="width: 3rem" />

        <!-- Task Name with Status Icon -->
        <Column field="task_name" header="Aufgabe">
          <template #body="slotProps">
            <div class="type-cell">
              <i 
                class="pi pi-circle-fill status-icon" 
                :class="slotProps.data.is_active ? 'status-active' : 'status-ended'"
                v-tooltip.top="slotProps.data.is_active ? 'Aktiv' : 'Beendet'"
              ></i>
              <span>{{ slotProps.data.task_name }}</span>
            </div>
          </template>
        </Column>

        <!-- Start Date -->
        <Column field="start_date" header="Start">
          <template #body="slotProps">
            {{ formatDate(slotProps.data.start_date) }}
          </template>
        </Column>
        
        <!-- End Date -->
        <Column field="end_date" header="Ende">
          <template #body="slotProps">
            {{ formatDate(slotProps.data.end_date) }}
          </template>
        </Column>

        <!-- Actions -->
        <Column header="Aktionen" headerStyle="width: 10rem">
          <template #body="slotProps">
            <div class="action-buttons">
              <Button
                v-if="slotProps.data.is_active"
                icon="pi pi-times-circle"
                text
                size="small"
                severity="warning"
                @click.stop="confirmEndTask(slotProps.data)"
                v-tooltip.top="'Beenden'"
              />
              <Button
                icon="pi pi-pencil"
                text
                size="small"
                severity="secondary"
                @click.stop="editTask(slotProps.data)"
                v-tooltip.top="'Bearbeiten'"
              />
              <Button
                icon="pi pi-trash"
                text
                size="small"
                severity="danger"
                @click.stop="confirmDelete(slotProps.data)"
                v-tooltip.top="'Löschen'"
              />
            </div>
          </template>
        </Column>

        <!-- Expansion Row Template -->
        <template #expansion="slotProps">
          <div class="expansion-content">
            <!-- Details Section -->
            <div class="details-section">
              <h4><i class="pi pi-info-circle"></i> Details</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="label">Startdatum:</span>
                  <span class="value">{{ formatDate(slotProps.data.start_date) }}</span>
                </div>
                <div v-if="slotProps.data.end_date" class="detail-item">
                  <span class="label">Enddatum:</span>
                  <span class="value">{{ formatDate(slotProps.data.end_date) }}</span>
                </div>
                <div v-if="slotProps.data.duration_days" class="detail-item">
                  <span class="label">Dauer:</span>
                  <span class="value">{{ slotProps.data.duration_days }} Tage</span>
                </div>
                <div class="detail-item">
                  <span class="label">Status:</span>
                  <Tag
                    :value="slotProps.data.is_active ? 'Aktiv' : 'Beendet'"
                    :severity="slotProps.data.is_active ? 'success' : 'secondary'"
                  />
                </div>
                <div v-if="slotProps.data.note" class="detail-item full-width">
                  <span class="label">Notizen:</span>
                  <p class="notes-text">{{ slotProps.data.note }}</p>
                </div>
              </div>
            </div>

            <!-- Attachments Section -->
            <div class="attachments-section">
              <AttachmentsSection
                :source-id="slotProps.data.id"
                source-type="specialTask"
                :initial-attachments="slotProps.data.attachments || []"
              />
            </div>
          </div>
        </template>
      </DataTable>
    </div>

    <!-- Create/Edit Dialog -->
    <Dialog
      v-model:visible="showCreateDialog"
      :header="editingTaskId ? 'Sonderaufgabe bearbeiten' : 'Neue Sonderaufgabe'"
      :style="{ width: '600px' }"
      modal
    >
      <SpecialTaskForm
        :task-id="editingTaskId || undefined"
        :default-member-id="memberId"
        @success="handleSuccess"
        @cancel="closeDialog"
      />
    </Dialog>

    <!-- End Task Dialog -->
    <Dialog
      v-model:visible="showEndDialog"
      header="Sonderaufgabe beenden"
      :style="{ width: '500px' }"
      modal
    >
      <div class="end-task-dialog">
        <p>Möchten Sie die Sonderaufgabe "{{ endingTask?.task_name }}" beenden?</p>
        <div class="input-group">
          <label for="end_date">Enddatum:</label>
          <InputText
            id="end_date"
            v-model="endDateString"
            type="date"
          />
        </div>
      </div>
      <template #footer>
        <Button
          label="Abbrechen"
          icon="pi pi-times"
          text
          @click="showEndDialog = false"
        />
        <Button
          label="Beenden"
          icon="pi pi-check"
          @click="endTask"
          :loading="loading"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useQualificationsStore } from '@/stores/qualifications'
import type { SpecialTask } from '@/types/qualifications'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import SpecialTaskForm from '@/components/qualifications/organisms/SpecialTaskForm.vue'
import AttachmentsSection from '@/components/qualifications/organisms/AttachmentsSection.vue'

interface Props {
  memberId: number
}

const props = defineProps<Props>()
const toast = useToast()
const confirm = useConfirm()
const qualificationsStore = useQualificationsStore()

const loading = ref(false)
const showCreateDialog = ref(false)
const showEndDialog = ref(false)
const editingTaskId = ref<number | null>(null)
const endingTask = ref<SpecialTask | null>(null)
const expandedRows = ref<Record<number, boolean>>({})
const endDateString = ref<string>((new Date().toISOString().split('T')[0] as string))

// No need to filter locally - the API already filtered by member
// The store's specialTasks array contains only this member's tasks after fetchSpecialTasks({ member: props.memberId })
const memberSpecialTasks = computed(() => qualificationsStore.specialTasks)

const hasSpecialTasks = computed(() => memberSpecialTasks.value.length > 0)

onMounted(async () => {
  await loadSpecialTasks()
})

const loadSpecialTasks = async () => {
  try {
    loading.value = true
    await qualificationsStore.fetchSpecialTasks({ member: props.memberId })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Sonderaufgaben konnten nicht geladen werden',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const onRowExpand = async (event: { data: SpecialTask }) => {
  // Load full details when row expands
  try {
    await qualificationsStore.fetchSpecialTask(event.data.id)
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Details konnten nicht geladen werden',
      life: 3000
    })
  }
}

const onRowCollapse = () => {
  // Optional: cleanup if needed
}

const editTask = (task: SpecialTask) => {
  editingTaskId.value = task.id
  showCreateDialog.value = true
}

const confirmEndTask = (task: SpecialTask) => {
  endingTask.value = task
  const today = new Date().toISOString().split('T')[0]
  endDateString.value = today as string
  showEndDialog.value = true
}

const endTask = async () => {
  if (!endingTask.value) return

  try {
    loading.value = true
    
    const today = new Date().toISOString().split('T')[0]
    
    // If user selected today's date, just call end_task endpoint
    // Otherwise, update with the selected end_date
    if (endDateString.value === today) {
      await qualificationsStore.endSpecialTask(endingTask.value.id)
    } else {
      // User chose a different date - just update the end_date
      await qualificationsStore.updateSpecialTask(endingTask.value.id, {
        end_date: endDateString.value
      })
    }
    
    await loadSpecialTasks()
    
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: 'Sonderaufgabe wurde beendet',
      life: 3000
    })
    
    // Close dialog and clear state AFTER success
    showEndDialog.value = false
    // Use setTimeout to wait for dialog close animation
    setTimeout(() => {
      endingTask.value = null
    }, 300)
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Sonderaufgabe konnte nicht beendet werden',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const confirmDelete = (task: SpecialTask) => {
  confirm.require({
    message: `Möchten Sie die Sonderaufgabe "${task.task_name}" wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await qualificationsStore.deleteSpecialTask(task.id)
        await loadSpecialTasks()
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Sonderaufgabe wurde gelöscht',
          life: 3000
        })
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Sonderaufgabe konnte nicht gelöscht werden',
          life: 3000
        })
      }
    }
  })
}

const handleSuccess = async () => {
  closeDialog()
  await loadSpecialTasks()
  toast.add({
    severity: 'success',
    summary: 'Erfolg',
    detail: editingTaskId.value
      ? 'Sonderaufgabe wurde aktualisiert'
      : 'Sonderaufgabe wurde hinzugefügt',
    life: 3000
  })
}

const closeDialog = () => {
  showCreateDialog.value = false
  editingTaskId.value = null
}

const formatDate = (dateString: string | null): string => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('de-DE')
}
</script>

<style scoped>
.specialtasks-manager {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 1.25rem;
  color: var(--text-color);
}

.section-header h3 i {
  color: var(--primary-color);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  gap: 1rem;
  text-align: center;
}

.empty-state p {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 1.1rem;
}

/* TreeTable Styles */
.specialtasks-treetable :deep(.p-datatable) {
  border-radius: 8px;
  overflow: hidden;
}

.type-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-icon {
  font-size: 0.75rem;
  flex-shrink: 0;
}

.status-icon.status-active {
  color: var(--p-tag-success-color);
}

.status-icon.status-ended {
  color: var(--p-tag-danger-color);
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
  justify-content: flex-end;
}

/* Expansion Content */
.expansion-content {
  background: var(--surface-50);
  padding: 1.5rem;
  border-left: 3px solid var(--primary-color);
  margin: 0.5rem 0;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.details-section h4,
.attachments-section h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: var(--text-color);
  font-weight: 600;
}

.details-section h4 i {
  color: var(--primary-color);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-item.full-width {
  grid-column: 1 / -1;
}

.detail-item .label {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  font-weight: 500;
}

.detail-item .value {
  color: var(--text-color);
  font-size: 1rem;
}

.notes-text {
  margin: 0.5rem 0 0 0;
  padding: 0.75rem;
  background: var(--surface-card);
  border-radius: 6px;
  border-left: 3px solid var(--primary-color);
  color: var(--text-color);
  line-height: 1.5;
}

/* End Task Dialog */
.end-task-dialog {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.end-task-dialog p {
  margin: 0;
  color: var(--text-color);
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.input-group label {
  font-weight: 600;
  color: var(--text-color);
}

@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .section-header :deep(.p-button) {
    width: 100%;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .expansion-content {
    padding: 1rem;
  }

  /* Hide end date column on mobile (keep start date) */
  .specialtasks-treetable :deep(.p-datatable-tbody > tr > td:nth-child(4)) {
    display: none;
  }

  .specialtasks-treetable :deep(.p-datatable-thead > tr > th:nth-child(4)) {
    display: none;
  }
}
</style>

