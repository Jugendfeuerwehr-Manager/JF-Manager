<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQualificationsStore } from '@/stores/qualifications'
import AttachmentsSection from '@/components/qualifications/organisms/AttachmentsSection.vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

const route = useRoute()
const router = useRouter()
const qualificationsStore = useQualificationsStore()
const confirm = useConfirm()
const toast = useToast()

const taskId = computed(() => Number(route.params.id))
const specialTask = computed(() => qualificationsStore.currentSpecialTask)
const loading = computed(() => qualificationsStore.loadingDetail)
const loadError = ref<string | null>(null)

function formatDate(value: string | null): string {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('de-DE')
}

function getStatusSeverity(): 'success' | 'warning' {
  if (!specialTask.value) return 'success'
  return specialTask.value.is_active ? 'success' : 'warning'
}

function getStatusLabel(): string {
  if (!specialTask.value) return ''
  return specialTask.value.is_active ? 'Aktiv' : 'Beendet'
}

async function loadSpecialTask() {
  if (!taskId.value) {
    loadError.value = 'Ungültige Sonderaufgabe.'
    return
  }

  loadError.value = null

  try {
    await qualificationsStore.fetchSpecialTask(taskId.value)
  } catch (error: any) {
    console.error('Failed to load special task:', error)
    loadError.value = error?.message || 'Die Sonderaufgabe konnte nicht geladen werden.'
  }
}

function navigateBack() {
  router.push('/qualifications')
}

function navigateToEdit() {
  if (taskId.value) {
    router.push(`/qualifications/specialtasks/${taskId.value}/edit`)
  }
}

function handleEndTask() {
  if (!taskId.value || !specialTask.value?.is_active) return

  confirm.require({
    message: 'Möchtest du diese Sonderaufgabe als beendet markieren?',
    header: 'Sonderaufgabe beenden',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Beenden',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-warning',
    accept: async () => {
      try {
        await qualificationsStore.endSpecialTask(taskId.value)
        await loadSpecialTask()
        toast.add({
          severity: 'success',
          summary: 'Sonderaufgabe beendet',
          detail: 'Die Sonderaufgabe wurde erfolgreich beendet.',
          life: 3000
        })
      } catch (error: any) {
        console.error('Failed to end special task:', error)
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: error?.message || 'Sonderaufgabe konnte nicht beendet werden.',
          life: 4000
        })
      }
    }
  })
}

function handleDeleteTask() {
  if (!taskId.value) return

  confirm.require({
    message: 'Soll diese Sonderaufgabe dauerhaft gelöscht werden?',
    header: 'Sonderaufgabe löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await qualificationsStore.deleteSpecialTask(taskId.value)
        toast.add({
          severity: 'success',
          summary: 'Sonderaufgabe gelöscht',
          detail: 'Die Sonderaufgabe wurde entfernt.',
          life: 3000
        })
        navigateBack()
      } catch (error: any) {
        console.error('Failed to delete special task:', error)
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: error?.message || 'Sonderaufgabe konnte nicht gelöscht werden.',
          life: 4000
        })
      }
    }
  })
}

onMounted(loadSpecialTask)

watch(
  () => route.params.id,
  () => {
    loadSpecialTask()
  }
)
</script>

<template>
  <div>
    <div class="special-task-detail">
      <div class="detail-header">
        <Button
          label="Zur Übersicht"
          icon="pi pi-arrow-left"
          severity="secondary"
          outlined
          @click="navigateBack"
        />

        <div class="header-actions" v-if="specialTask">
          <Button label="Bearbeiten" icon="pi pi-pencil" @click="navigateToEdit" />
          <Button
            label="Beenden"
            icon="pi pi-check"
            severity="warning"
            outlined
            :disabled="!specialTask.is_active"
            @click="handleEndTask"
          />
          <Button
            label="Löschen"
            icon="pi pi-trash"
            severity="danger"
            outlined
            @click="handleDeleteTask"
          />
        </div>
      </div>

      <Message v-if="loadError" severity="error" :closable="false" class="mb-4">
        {{ loadError }}
      </Message>

      <Card v-if="loading" class="mb-4">
      <template #content>
        <div class="skeleton-grid">
          <Skeleton height="2rem" width="60%" />
          <Skeleton height="1.5rem" width="40%" />
          <div class="detail-grid">
            <Skeleton height="1.5rem" width="100%" v-for="index in 5" :key="index" />
          </div>
        </div>
      </template>
    </Card>

    <Card v-else-if="specialTask" class="mb-4">
      <template #title>
        <div class="title-bar">
          <div>
            <h2 class="title">{{ specialTask.task_name }}</h2>
            <p class="subtitle">{{ specialTask.person_name }}</p>
          </div>
          <Tag :severity="getStatusSeverity()" :value="getStatusLabel()" />
        </div>
      </template>
      <template #content>
        <div class="detail-grid">
          <div class="detail-row">
            <span class="detail-label">Startdatum</span>
            <span class="detail-value">{{ formatDate(specialTask.start_date) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Enddatum</span>
            <span class="detail-value">
              {{ specialTask.end_date ? formatDate(specialTask.end_date) : 'Noch aktiv' }}
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Dauer</span>
            <span class="detail-value">{{ specialTask.duration_days }} Tage</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Zugewiesen an Benutzer</span>
            <span class="detail-value">{{ specialTask.user_name || '-' }}</span>
          </div>
        </div>

        <div class="notes-section">
          <h3>Notizen</h3>
          <p v-if="specialTask.note" class="note">{{ specialTask.note }}</p>
          <p v-else class="note empty">Keine Notizen hinterlegt.</p>
        </div>
      </template>
    </Card>

      <AttachmentsSection
        v-if="specialTask"
        :source-id="specialTask.id"
        source-type="specialTask"
        :initial-attachments="specialTask.attachments || []"
      />
    </div>

    <ConfirmDialog />
  </div>
</template>

<style scoped>
.special-task-detail {
  padding: 1.5rem;
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.title-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.title {
  margin: 0;
  font-size: 1.5rem;
}

.subtitle {
  margin: 0;
  color: var(--text-color-secondary);
}

.detail-grid {
  display: grid;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--surface-border);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-weight: 600;
  color: var(--text-color-secondary);
}

.detail-value {
  color: var(--text-color);
}

.notes-section h3 {
  margin-top: 0;
}

.note {
  margin: 0;
  white-space: pre-line;
}

.note.empty {
  color: var(--text-color-secondary);
  font-style: italic;
}

.skeleton-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

@media (max-width: 768px) {
  .special-task-detail {
    padding: 1rem;
  }

  .detail-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }
}
</style>
