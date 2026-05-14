<template>
  <SettingsCategoryCard
    title="Mitglieder Synchronisation"
    description="Externe Quellen für Gruppen- und Mitgliederimport konfigurieren"
    icon="pi pi-refresh"
  >
    <div class="flex flex-column gap-4">
      <Message v-if="syncStore.error" severity="error" @close="syncStore.clearError()" closable>
        {{ syncStore.error }}
      </Message>

      <form class="sync-job-form" @submit.prevent="handleCreateJob">
        <div class="form-grid">
          <div class="field">
            <label for="sync-job-name">Name</label>
            <InputText id="sync-job-name" v-model="form.name" :disabled="!canEdit" />
          </div>

          <div class="field">
            <label for="sync-provider">Quelle</label>
            <Dropdown
              id="sync-provider"
              v-model="form.provider"
              :options="providerOptions"
              option-label="label"
              option-value="value"
              :disabled="!canEdit"
            />
          </div>

          <div class="field" v-if="form.provider === 'spond'">
            <label for="sync-operation-mode">Betriebsmodus</label>
            <Dropdown
              id="sync-operation-mode"
              v-model="form.config.operation_mode"
              :options="operationModeOptions"
              option-label="label"
              option-value="value"
              :disabled="!canEdit"
            />
          </div>

          <div class="field" v-if="form.provider !== 'spond' || form.config.operation_mode !== 'groups_to_departments'">
            <label for="sync-scope">Geltung</label>
            <Dropdown
              id="sync-scope"
              v-model="form.scope"
              :options="scopeOptions"
              option-label="label"
              option-value="value"
              :disabled="!canEdit"
            />
          </div>

          <div class="field" v-if="form.scope === 'department' && form.config.operation_mode !== 'groups_to_departments'">
            <label for="sync-department">Abteilung</label>
            <Dropdown
              id="sync-department"
              v-model="form.department"
              :options="departmentOptions"
              option-label="label"
              option-value="value"
              placeholder="Abteilung auswählen"
              :disabled="!canEdit"
            />
          </div>

          <div class="field">
            <label for="sync-run-mode">Ausführung</label>
            <Dropdown
              id="sync-run-mode"
              v-model="form.run_mode"
              :options="runModeOptions"
              option-label="label"
              option-value="value"
              :disabled="!canEdit"
            />
          </div>

          <div class="field" v-if="form.run_mode === 'interval'">
            <label for="sync-interval">Intervall (Minuten)</label>
            <InputNumber id="sync-interval" v-model="form.interval_minutes" :min="5" :disabled="!canEdit" />
          </div>

          <div class="field">
            <label for="sync-deletion-mode">Umgang mit entfernten Datensätzen</label>
            <Dropdown
              id="sync-deletion-mode"
              v-model="form.deletion_mode"
              :options="deletionModeOptions"
              option-label="label"
              option-value="value"
              :disabled="!canEdit"
            />
          </div>

          <div class="field field-checkbox">
            <Checkbox id="sync-enabled" v-model="form.enabled" :binary="true" :disabled="!canEdit" />
            <label for="sync-enabled">Job aktivieren</label>
          </div>
        </div>

        <div v-if="form.provider === 'spond'" class="credentials-grid">
          <div class="field">
            <label for="sync-cred-username">Spond E-Mail</label>
            <InputText id="sync-cred-username" v-model="form.credentials.username" :disabled="!canEdit" autocomplete="off" />
          </div>
          <div class="field">
            <label for="sync-cred-password">Spond Passwort</label>
            <Password
              id="sync-cred-password"
              v-model="form.credentials.password"
              :feedback="false"
              toggle-mask
              :disabled="!canEdit"
              input-class="w-full"
            />
          </div>
          <div class="field">
            <label for="sync-spond-group">Spond Top-Level-Gruppe</label>
            <Dropdown
              id="sync-spond-group"
              v-model="form.config.group_id"
              :options="spondTopLevelGroupOptions"
              option-label="label"
              option-value="value"
              placeholder="Top-Level-Gruppe auswählen"
              :disabled="!canEdit || syncStore.spondTopLevelGroups.length === 0"
            />
          </div>
          <div class="field field-action">
            <Button
              label="Spond-Gruppen laden"
              icon="pi pi-download"
              type="button"
              outlined
              @click="handleLoadSpondGroups"
              :disabled="!canEdit || !canLoadSpondGroups"
              :loading="syncStore.loading"
            />
          </div>
          <div class="field field-note">
            <small class="text-color-secondary">{{ operationModeDescription }}</small>
          </div>
        </div>

        <div class="flex justify-content-end mt-3">
          <Button label="Sync-Job anlegen" type="submit" :disabled="!canEdit || !canCreateJob" :loading="syncStore.loading" />
        </div>
      </form>

      <div>
        <div class="flex justify-content-between align-items-center mb-3">
          <h4 class="m-0">Jobs</h4>
          <Button icon="pi pi-refresh" text rounded @click="refreshData" :loading="syncStore.loading" />
        </div>

        <div v-if="syncStore.jobs.length === 0" class="empty-state">
          Noch keine Synchronisationsjobs vorhanden.
        </div>

        <div v-else class="job-list">
          <div v-for="job in syncStore.jobs" :key="job.id" class="job-card">
            <div class="job-card__header">
              <div>
                <h5 class="m-0">{{ job.name }}</h5>
                <p class="m-0 text-color-secondary text-sm">
                  {{ providerLabel(job.provider) }} · {{ operationModeLabel(job) }} · {{ scopeLabel(job) }} · {{ runModeLabel(job) }}
                </p>
              </div>
              <div class="flex gap-2 align-items-center">
                <Tag :value="job.enabled ? 'Aktiv' : 'Pausiert'" :severity="job.enabled ? 'success' : 'secondary'" />
                <Tag
                  v-if="job.last_test_status !== null"
                  :value="job.last_test_status ? 'Test OK' : 'Test fehlgeschlagen'"
                  :severity="job.last_test_status ? 'success' : 'danger'"
                />
              </div>
            </div>

            <div class="job-card__meta">
              <span>Letzter Lauf: {{ formatDateTime(job.last_run_at) }}</span>
              <span>Nächster Lauf: {{ formatDateTime(job.next_run_at) }}</span>
              <span>Letzt getestet: {{ formatDateTime(job.last_tested_at) }}</span>
            </div>

            <Message v-if="job.last_error" severity="warn" :closable="false">
              {{ job.last_error }}
            </Message>

            <div class="job-card__actions">
              <Button
                label="Testen"
                icon="pi pi-check-circle"
                text
                @click="handleTest(job.id)"
                :disabled="!canEdit || syncStore.actionJobId === job.id"
              />
              <Button
                label="Jetzt synchronisieren"
                icon="pi pi-play"
                text
                @click="handleRun(job.id)"
                :disabled="!canEdit || syncStore.actionJobId === job.id"
              />
              <Button
                label="Bereinigungsvorschau"
                icon="pi pi-trash"
                text
                @click="handlePreview(job.id)"
                :disabled="!canEdit || syncStore.actionJobId === job.id"
              />
              <Button
                label="Löschen"
                icon="pi pi-times"
                text
                severity="danger"
                @click="handleDelete(job.id)"
                :disabled="!canEdit || syncStore.actionJobId === job.id"
              />
            </div>
          </div>
        </div>
      </div>

      <div v-if="syncStore.garbageCollectionPreview" class="preview-box">
        <div class="flex justify-content-between align-items-center mb-2">
          <h4 class="m-0">Bereinigungsvorschau</h4>
          <Button
            label="Bereinigung ausführen"
            icon="pi pi-trash"
            severity="danger"
            @click="handleGarbageCollect(syncStore.garbageCollectionPreview.job)"
            :disabled="!canEdit || syncStore.actionJobId === syncStore.garbageCollectionPreview.job"
          />
        </div>

        <p class="m-0 mb-2">Vorgemerkte Objekte: {{ syncStore.garbageCollectionPreview.pending_count }}</p>

        <ul class="preview-list">
          <li v-for="item in syncStore.garbageCollectionPreview.items" :key="item.id">
            {{ previewObjectTypeLabel(item.object_type) }} · {{ item.external_name || item.external_id }}
          </li>
        </ul>
      </div>

      <div>
        <h4 class="mb-3">Letzte Läufe</h4>
        <DataTable :value="syncStore.runs" striped-rows size="small">
          <Column field="job_name" header="Job" />
          <Column field="status" header="Status">
            <template #body="{ data }">
              <Tag :value="data.status" :severity="runSeverity(data.status)" />
            </template>
          </Column>
          <Column field="trigger" header="Auslöser" />
          <Column field="created_at" header="Zeitpunkt">
            <template #body="{ data }">
              {{ formatDateTime(data.created_at) }}
            </template>
          </Column>
          <Column field="error_message" header="Hinweis">
            <template #body="{ data }">
              {{ data.error_message || '-' }}
            </template>
          </Column>
        </DataTable>
      </div>
    </div>
  </SettingsCategoryCard>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Password from 'primevue/password'
import Tag from 'primevue/tag'

import { useDepartmentsStore } from '@/stores/departments'
import { useExternalSyncStore } from '@/stores/externalSync'
import type {
  SpondOperationMode,
  SyncDeletionMode,
  SyncJob,
  SyncJobCreate,
  SyncProvider,
  SyncRunMode,
  SyncRunStatus,
  SyncScope,
} from '@/types/externalSync'
import { getSpondOperationMode } from '@/types/externalSync'
import { getApiErrorMessage } from '@/utils/apiError'

import SettingsCategoryCard from '../atoms/SettingsCategoryCard.vue'

interface Props {
  canEdit: boolean
}

defineProps<Props>()
const toast = useToast()
const syncStore = useExternalSyncStore()
const departmentsStore = useDepartmentsStore()

const form = reactive<
  SyncJobCreate & {
    credentials: { username: string; password: string }
    config: { group_id: string | null; operation_mode: SpondOperationMode }
  }
>({
  name: '',
  provider: 'spond',
  scope: 'organization',
  department: null,
  run_mode: 'manual',
  interval_minutes: null,
  deletion_mode: 'review',
  enabled: true,
  credentials: { username: '', password: '' },
  config: { group_id: null, operation_mode: 'groups_to_groups' },
})

const providerOptions: Array<{ label: string; value: SyncProvider }> = [
  { label: 'Spond', value: 'spond' },
  { label: 'Hi-Org', value: 'hi_org' },
]

const scopeOptions: Array<{ label: string; value: SyncScope }> = [
  { label: 'Organisation', value: 'organization' },
  { label: 'Abteilung', value: 'department' },
]

const operationModeOptions: Array<{ label: string; value: SpondOperationMode }> = [
  { label: 'Spond-Gruppen zu Gruppen', value: 'groups_to_groups' },
  { label: 'Spond-Gruppen zu Abteilungen', value: 'groups_to_departments' },
  { label: 'Nur Mitglieder', value: 'members_only' },
]

const runModeOptions: Array<{ label: string; value: SyncRunMode }> = [
  { label: 'Nur manuell', value: 'manual' },
  { label: 'Intervall', value: 'interval' },
]

const deletionModeOptions: Array<{ label: string; value: SyncDeletionMode }> = [
  { label: 'Zur Prüfung markieren', value: 'review' },
  { label: 'Automatisch löschen', value: 'auto_delete' },
]

const departmentOptions = computed(() =>
  departmentsStore.departments.map((department) => ({ label: department.name, value: department.id })),
)

const spondTopLevelGroupOptions = computed(() =>
  syncStore.spondTopLevelGroups.map((group) => ({ label: group.name, value: group.id })),
)

const canLoadSpondGroups = computed(
  () =>
    form.provider === 'spond' &&
    form.credentials.username.trim().length > 0 &&
    form.credentials.password.trim().length > 0,
)

const canCreateJob = computed(() => {
  if (!form.name.trim()) {
    return false
  }
  if (form.scope === 'department' && form.config.operation_mode !== 'groups_to_departments' && !form.department) {
    return false
  }
  if (form.run_mode === 'interval' && !form.interval_minutes) {
    return false
  }
  if (form.provider === 'spond' && (!form.credentials.username.trim() || !form.credentials.password.trim())) {
    return false
  }
  if (form.provider === 'spond' && !form.config.group_id) {
    return false
  }
  return true
})

const operationModeDescription = computed(() => {
  switch (form.config.operation_mode) {
    case 'groups_to_departments':
      return 'Spond-Untergruppen werden als Abteilungen zugeordnet oder neu angelegt. Mitglieder werden nur den passenden Abteilungen zugewiesen.'
    case 'members_only':
      return 'Es werden nur Mitgliederdaten synchronisiert. Es werden keine Gruppen oder Abteilungen aus Spond erstellt.'
    default:
      return 'Spond-Untergruppen werden als JF-Gruppen synchronisiert und Mitglieder der ermittelten Gruppe zugewiesen.'
  }
})

watch(
  () => form.provider,
  (provider) => {
    if (provider !== 'spond') {
      form.config.group_id = null
      syncStore.clearSpondTopLevelGroups()
      form.scope = 'organization'
    }
  },
)

watch(
  () => form.config.operation_mode,
  (operationMode) => {
    if (operationMode === 'groups_to_departments') {
      form.scope = 'organization'
      form.department = null
    }
  },
)

watch(
  [() => form.credentials.username, () => form.credentials.password],
  () => {
    form.config.group_id = null
    syncStore.clearSpondTopLevelGroups()
  },
)

onMounted(async () => {
  try {
    if (departmentsStore.departments.length === 0) {
      await departmentsStore.fetchDepartments()
    }
    await refreshData()
  } catch {
    // Errors are surfaced through the store message.
  }
})

async function refreshData() {
  await Promise.all([syncStore.fetchJobs(), syncStore.fetchRuns()])
}

async function handleLoadSpondGroups() {
  try {
    await syncStore.fetchSpondTopLevelGroups({
      username: form.credentials.username.trim(),
      password: form.credentials.password,
    })
    toast.add({ severity: 'success', summary: 'Spond', detail: 'Top-Level-Gruppen geladen', life: 3000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Spond', detail: getApiErrorMessage(err, 'Spond-Gruppen konnten nicht geladen werden'), life: 5000 })
  }
}

async function handleCreateJob() {
  try {
    await syncStore.createJob({
      ...form,
      interval_minutes: form.run_mode === 'interval' ? form.interval_minutes : null,
      department: form.scope === 'department' ? form.department : null,
      config:
        form.provider === 'spond'
          ? {
              group_id: form.config.group_id,
              operation_mode: form.config.operation_mode,
            }
          : undefined,
      credentials: form.provider === 'spond' ? { username: form.credentials.username, password: form.credentials.password } : undefined,
    })
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'Sync-Job angelegt', life: 3000 })
    resetForm()
    await refreshData()
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Fehler', detail: getApiErrorMessage(err, 'Sync-Job konnte nicht angelegt werden'), life: 5000 })
  }
}

async function handleTest(jobId: number) {
  try {
    await syncStore.testConnection(jobId)
    toast.add({ severity: 'success', summary: 'Verbindung', detail: 'Verbindungstest erfolgreich', life: 3000 })
  } catch (err) {
    toast.add({ severity: 'warn', summary: 'Verbindung', detail: getApiErrorMessage(err, 'Verbindungstest fehlgeschlagen'), life: 5000 })
  }
}

async function handleRun(jobId: number) {
  try {
    await syncStore.runNow(jobId)
    toast.add({ severity: 'success', summary: 'Synchronisation', detail: 'Synchronisation abgeschlossen', life: 3000 })
  } catch (err) {
    toast.add({ severity: 'warn', summary: 'Synchronisation', detail: getApiErrorMessage(err, 'Synchronisation fehlgeschlagen'), life: 5000 })
  }
}

async function handlePreview(jobId: number) {
  try {
    await syncStore.fetchGarbageCollectionPreview(jobId)
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Bereinigung', detail: getApiErrorMessage(err, 'Bereinigungsvorschau fehlgeschlagen'), life: 5000 })
  }
}

async function handleGarbageCollect(jobId: number) {
  try {
    const result = await syncStore.garbageCollect(jobId)
    toast.add({ severity: 'success', summary: 'Bereinigung', detail: `${result.deleted_count} Einträge entfernt`, life: 3000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Bereinigung', detail: getApiErrorMessage(err, 'Bereinigung fehlgeschlagen'), life: 5000 })
  }
}

async function handleDelete(jobId: number) {
  try {
    await syncStore.deleteJob(jobId)
    toast.add({ severity: 'success', summary: 'Gelöscht', detail: 'Sync-Job gelöscht', life: 3000 })
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Fehler', detail: getApiErrorMessage(err, 'Sync-Job konnte nicht gelöscht werden'), life: 5000 })
  }
}

function resetForm() {
  form.name = ''
  form.provider = 'spond'
  form.scope = 'organization'
  form.department = null
  form.run_mode = 'manual'
  form.interval_minutes = null
  form.deletion_mode = 'review'
  form.enabled = true
  form.credentials = { username: '', password: '' }
  form.config = { group_id: null, operation_mode: 'groups_to_groups' }
  syncStore.clearSpondTopLevelGroups()
}

function providerLabel(provider: SyncProvider) {
  return providerOptions.find((option) => option.value === provider)?.label ?? provider
}

function scopeLabel(job: SyncJob) {
  if (job.provider === 'spond' && getSpondOperationMode(job.config) === 'groups_to_departments') {
    return 'Abteilungs-Sync (organisationsweit)'
  }
  return job.scope === 'organization' ? 'Organisation' : job.department_name || 'Abteilung'
}

function operationModeLabel(job: SyncJob) {
  if (job.provider !== 'spond') {
    return 'Standard'
  }

  switch (getSpondOperationMode(job.config)) {
    case 'groups_to_departments':
      return 'Gruppen -> Abteilungen'
    case 'members_only':
      return 'Nur Mitglieder'
    default:
      return 'Gruppen -> Gruppen'
  }
}

function runModeLabel(job: SyncJob) {
  if (job.run_mode === 'interval' && job.interval_minutes) {
    return `alle ${job.interval_minutes} min`
  }
  return 'nur manuell'
}

function runSeverity(status: SyncRunStatus) {
  switch (status) {
    case 'succeeded':
      return 'success'
    case 'failed':
      return 'danger'
    case 'running':
      return 'info'
    case 'cancelled':
      return 'warn'
    default:
      return 'secondary'
  }
}

function formatDateTime(value: string | null) {
  if (!value) {
    return '-'
  }

  return new Intl.DateTimeFormat('de-DE', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

function previewObjectTypeLabel(objectType: 'member' | 'group' | 'department') {
  if (objectType === 'member') {
    return 'Mitglied'
  }
  if (objectType === 'department') {
    return 'Abteilung'
  }
  return 'Gruppe'
}
</script>

<style scoped>
.sync-job-form {
  border: 1px solid var(--surface-border);
  border-radius: 0.75rem;
  padding: 1rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-checkbox {
  flex-direction: row;
  align-items: center;
  margin-top: 1.75rem;
}

.field-action {
  justify-content: flex-end;
}

.field-note {
  justify-content: center;
}

.credentials-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}

.job-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.job-card {
  border: 1px solid var(--surface-border);
  border-radius: 0.75rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.job-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.job-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.job-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.preview-box {
  border: 1px solid var(--surface-border);
  border-radius: 0.75rem;
  padding: 1rem;
  background: var(--surface-50);
}

.preview-list {
  margin: 0;
  padding-left: 1.25rem;
}

.empty-state {
  border: 1px dashed var(--surface-border);
  border-radius: 0.75rem;
  padding: 1rem;
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .job-card__header {
    flex-direction: column;
  }
}
</style>
