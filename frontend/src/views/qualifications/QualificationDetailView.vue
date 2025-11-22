<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQualificationsStore } from '@/stores/qualifications'
import AttachmentsSection from '@/components/qualifications/organisms/AttachmentsSection.vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'
import Message from 'primevue/message'
import Skeleton from 'primevue/skeleton'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'

const route = useRoute()
const router = useRouter()
const qualificationsStore = useQualificationsStore()
const confirm = useConfirm()
const toast = useToast()

const qualificationId = computed(() => Number(route.params.id))
const qualification = computed(() => qualificationsStore.currentQualification)
const loading = computed(() => qualificationsStore.loadingDetail)
const loadError = ref<string | null>(null)

function getStatusSeverity(): 'success' | 'warning' | 'danger' {
  if (!qualification.value) return 'success'
  if (qualification.value.is_expired) return 'danger'
  if (qualification.value.expires_soon) return 'warning'
  return 'success'
}

function getStatusLabel(): string {
  if (!qualification.value) return ''
  if (qualification.value.is_expired) return 'Abgelaufen'
  if (qualification.value.expires_soon) return 'Läuft bald ab'
  return 'Gültig'
}

function formatDate(value: string | null): string {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('de-DE')
}

async function loadQualification() {
  if (!qualificationId.value) {
    loadError.value = 'Ungültige Qualifikation.'
    return
  }

  loadError.value = null

  try {
    await qualificationsStore.fetchQualification(qualificationId.value)
  } catch (error: any) {
    console.error('Failed to load qualification:', error)
    loadError.value = error?.message || 'Die Qualifikation konnte nicht geladen werden.'
  }
}

function navigateBack() {
  router.push('/qualifications')
}

function navigateToEdit() {
  if (qualificationId.value) {
    router.push(`/qualifications/${qualificationId.value}/edit`)
  }
}

function handleDelete() {
  if (!qualificationId.value) return

  confirm.require({
    message: 'Soll diese Qualifikation dauerhaft gelöscht werden?',
    header: 'Qualifikation löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await qualificationsStore.deleteQualification(qualificationId.value)
        toast.add({
          severity: 'success',
          summary: 'Qualifikation gelöscht',
          detail: 'Die Qualifikation wurde entfernt.',
          life: 3000
        })
        navigateBack()
      } catch (error: any) {
        console.error('Failed to delete qualification:', error)
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: error?.message || 'Qualifikation konnte nicht gelöscht werden.',
          life: 4000
        })
      }
    }
  })
}

onMounted(loadQualification)

watch(
  () => route.params.id,
  () => {
    loadQualification()
  }
)
</script>

<template>
  <div>
    <div class="qualification-detail">
      <div class="detail-header">
        <Button
          label="Zur Übersicht"
          icon="pi pi-arrow-left"
          severity="secondary"
          outlined
          @click="navigateBack"
        />

        <div class="header-actions" v-if="qualification">
          <Button label="Bearbeiten" icon="pi pi-pencil" @click="navigateToEdit" />
          <Button
            label="Löschen"
            icon="pi pi-trash"
            severity="danger"
            outlined
            @click="handleDelete"
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
            <Skeleton height="1.5rem" width="100%" v-for="index in 6" :key="index" />
          </div>
        </div>
      </template>
    </Card>

    <Card v-else-if="qualification" class="mb-4">
      <template #title>
        <div class="title-bar">
          <div>
            <h2 class="title">{{ qualification.type_name }}</h2>
            <p class="subtitle">{{ qualification.person_name }}</p>
          </div>
          <Tag :severity="getStatusSeverity()" :value="getStatusLabel()" />
        </div>
      </template>
      <template #content>
        <div class="detail-grid">
          <div class="detail-row">
            <span class="detail-label">Erworben am</span>
            <span class="detail-value">{{ formatDate(qualification.date_acquired) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Gültig bis</span>
            <span class="detail-value">{{ formatDate(qualification.date_expires) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Ausgestellt von</span>
            <span class="detail-value">{{ qualification.issued_by || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Zugewiesen an Benutzer</span>
            <span class="detail-value">{{ qualification.user_name || '-' }}</span>
          </div>
        </div>

        <Divider />

        <div>
          <h3>Notizen</h3>
          <p class="note" v-if="qualification.note">{{ qualification.note }}</p>
          <p class="note empty" v-else>Keine Notizen hinterlegt.</p>
        </div>
      </template>
    </Card>

    <AttachmentsSection
      v-if="qualification"
      :source-id="qualification.id"
      source-type="qualification"
      :initial-attachments="qualification.attachments || []"
    />
    </div>

  </div>
</template>

<style scoped>
.qualification-detail {
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
  .qualification-detail {
    padding: 1rem;
  }

  .detail-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
  }
}
</style>
