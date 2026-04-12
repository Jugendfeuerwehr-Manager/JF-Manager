<template>
  <div class="qualifications-manager">
    <!-- Header with Add Button -->
    <div class="section-header">
      <h3>
        <i class="pi pi-graduation-cap"></i>
        Qualifikationen
      </h3>
      <Button
        label="Qualifikation hinzufügen"
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
    <div v-else-if="!hasQualifications" class="empty-state">
      <i class="pi pi-graduation-cap" style="font-size: 3rem; color: var(--text-color-secondary)"></i>
      <p>Noch keine Qualifikationen vorhanden</p>
      <Button
        label="Erste Qualifikation hinzufügen"
        icon="pi pi-plus"
        @click="showCreateDialog = true"
      />
    </div>

    <!-- Qualifications TreeTable -->
    <div v-else class="qualifications-treetable">
      <DataTable
        :value="memberQualifications"
        :expandedRows="expandedRows"
        @rowExpand="onRowExpand"
        @rowCollapse="onRowCollapse"
        dataKey="id"
        responsiveLayout="scroll"
        stripedRows
      >
        <!-- Expander Column -->
        <Column :expander="true" headerStyle="width: 3rem" />

        <!-- Type Name with Status Icon -->
        <Column field="type_name" header="Typ">
          <template #body="slotProps">
            <div class="type-cell">
              <i 
                class="pi pi-circle-fill status-icon" 
                :class="getStatusClass(slotProps.data)"
                v-tooltip.top="getStatusLabel(slotProps.data)"
              ></i>
              <span>{{ slotProps.data.type_name }}</span>
            </div>
          </template>
        </Column>

        <!-- Date Acquired -->
        <Column field="date_acquired" header="Erworben">
          <template #body="slotProps">
            {{ formatDate(slotProps.data.date_acquired) }}
          </template>
        </Column>
        
        <!-- Date Expires -->
        <Column field="date_expires" header="Gültig bis">
          <template #body="slotProps">
            {{ formatDate(slotProps.data.date_expires) }}
          </template>
        </Column>

        <!-- Actions -->
        <Column header="Aktionen" headerStyle="width: 8rem">
          <template #body="slotProps">
            <div class="action-buttons">
              <Button
                icon="pi pi-pencil"
                text
                size="small"
                severity="secondary"
                @click.stop="editQualification(slotProps.data)"
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
                  <span class="label">Erworben:</span>
                  <span class="value">{{ formatDate(slotProps.data.date_acquired) }}</span>
                </div>
                <div v-if="slotProps.data.date_expires" class="detail-item">
                  <span class="label">Gültig bis:</span>
                  <span class="value">{{ formatDate(slotProps.data.date_expires) }}</span>
                </div>
                <div v-if="slotProps.data.issued_by" class="detail-item">
                  <span class="label">Ausgestellt von:</span>
                  <span class="value">{{ slotProps.data.issued_by }}</span>
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
                source-type="qualification"
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
      :header="editingQualificationId ? 'Qualifikation bearbeiten' : 'Neue Qualifikation'"
      :style="{ width: '600px' }"
      modal
    >
      <QualificationForm
        :qualification-id="editingQualificationId || undefined"
        :default-member-id="memberId"
        @success="handleSuccess"
        @cancel="closeDialog"
      />
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useQualificationsStore } from '@/stores/qualifications'
import type { Qualification } from '@/types/qualifications'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import QualificationForm from '@/components/qualifications/organisms/QualificationForm.vue'
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
const editingQualificationId = ref<number | null>(null)
const expandedRows = ref<Record<number, boolean>>({})

// No need to filter locally - the API already filtered by member
// The store's qualifications array contains only this member's qualifications after fetchQualifications({ member: props.memberId })
const memberQualifications = computed(() => qualificationsStore.qualifications)

const hasQualifications = computed(() => memberQualifications.value.length > 0)

onMounted(async () => {
  await loadQualifications()
})

const loadQualifications = async () => {
  try {
    loading.value = true
    await qualificationsStore.fetchQualifications({ member: props.memberId })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Qualifikationen konnten nicht geladen werden',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const onRowExpand = async (event: { data: Qualification }) => {
  // Load full details when row expands
  try {
    await qualificationsStore.fetchQualification(event.data.id)
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

const editQualification = (qualification: Qualification) => {
  editingQualificationId.value = qualification.id
  showCreateDialog.value = true
}

const confirmDelete = (qualification: Qualification) => {
  confirm.require({
    message: `Möchten Sie die Qualifikation "${qualification.type_name}" wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await qualificationsStore.deleteQualification(qualification.id)
        await loadQualifications()
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Qualifikation wurde gelöscht',
          life: 3000
        })
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Qualifikation konnte nicht gelöscht werden',
          life: 3000
        })
      }
    }
  })
}

const handleSuccess = async () => {
  closeDialog()
  await loadQualifications()
  toast.add({
    severity: 'success',
    summary: 'Erfolg',
    detail: editingQualificationId.value
      ? 'Qualifikation wurde aktualisiert'
      : 'Qualifikation wurde hinzugefügt',
    life: 3000
  })
}

const closeDialog = () => {
  showCreateDialog.value = false
  editingQualificationId.value = null
}

const getStatusLabel = (qualification: Qualification): string => {
  if (qualification.is_expired) return 'Abgelaufen'
  if (qualification.expires_soon) return 'Läuft bald ab'
  return 'Gültig'
}

const getStatusClass = (qualification: Qualification): string => {
  if (qualification.is_expired) return 'status-expired'
  if (qualification.expires_soon) return 'status-warning'
  return 'status-valid'
}

const formatDate = (dateString: string | null): string => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('de-DE')
}
</script>

<style scoped>
.qualifications-manager {
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
.qualifications-treetable :deep(.p-datatable) {
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

.status-icon.status-valid {
  color: var(--p-tag-success-color);
}

.status-icon.status-warning {
  color: var(--p-tag-warn-color);
}

.status-icon.status-expired {
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

  /* Hide expires column on mobile (keep acquired date) */
  .qualifications-treetable :deep(.p-datatable-tbody > tr > td:nth-child(4)) {
    display: none;
  }

  .qualifications-treetable :deep(.p-datatable-thead > tr > th:nth-child(4)) {
    display: none;
  }
}
</style>
