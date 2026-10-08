<template>
  <form class="service-form" novalidate @submit.prevent="handleSubmit">
    <Message v-if="serverTimeDivergent" severity="warn" :closable="false">
      <span>
        <strong>Zeitabweichung erkannt:</strong> Die Serverzeit weicht um
        {{ serverTimeDiffMinutes !== null ? Math.abs(serverTimeDiffMinutes) : '' }} Minuten von deiner
        lokalen Zeit ab. Die Standardzeiten beziehen sich auf deine lokale Uhrzeit.
      </span>
    </Message>

    <section class="form-card" aria-labelledby="service-time-title">
      <div class="form-card__header">
        <h2 id="service-time-title">Termin</h2>
        <Button
          type="button"
          label="Heute, Standardzeit"
          icon="pi pi-clock"
          severity="secondary"
          outlined
          :disabled="loading"
          @click="setTodayWithDefaultTime"
        />
      </div>
      <div class="form-grid">
        <div class="form-field">
          <label for="start">Beginn</label>
          <Calendar
            input-id="start"
            v-model="formData.start"
            updateModelType="date"
            showTime
            hourFormat="24"
            dateFormat="dd.mm.yy"
            showIcon
            :showButtonBar="true"
            :invalid="!!errors.start"
          />
          <p v-if="errors.start" class="field-error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors.start }}</p>
        </div>
        <div class="form-field">
          <label for="end">Ende</label>
          <Calendar
            input-id="end"
            v-model="formData.end"
            updateModelType="date"
            showTime
            hourFormat="24"
            dateFormat="dd.mm.yy"
            showIcon
            :showButtonBar="true"
            :invalid="!!errors.end"
          />
          <p v-if="errors.end" class="field-error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors.end }}</p>
        </div>
      </div>
    </section>

    <section class="form-card" aria-labelledby="service-content-title">
      <h2 id="service-content-title">Inhalt</h2>
      <div class="form-grid">
        <div class="form-field">
          <label for="topic">Thema</label>
          <InputText id="topic" v-model="formData.topic" placeholder="z. B. Übung: Erste Hilfe" />
        </div>
        <div class="form-field">
          <label for="place">Ort</label>
          <InputText id="place" v-model="formData.place" placeholder="z. B. Gerätehaus" />
        </div>
        <div class="form-field form-field--wide">
          <span id="operations-manager-label" class="field-label">Leitung</span>
          <UserChipSelector
            v-model="formData.operations_manager_ids"
            :options="usersOptions"
            :loading="usersLoading"
            :searchable="true"
            aria-labelledby="operations-manager-label"
          />
        </div>
        <div class="form-field form-field--wide">
          <label for="description">Beschreibung <span class="field-optional">(optional)</span></label>
          <Textarea id="description" v-model="formData.description" rows="3" auto-resize placeholder="Was ist geplant?" />
        </div>
      </div>
    </section>

    <section class="form-card" aria-labelledby="service-followup-title">
      <h2 id="service-followup-title">Nachbereitung</h2>
      <div class="form-field">
        <label for="events">Besondere Vorkommnisse <span class="field-optional">(optional)</span></label>
        <Textarea id="events" v-model="formData.events" rows="3" auto-resize placeholder="Verletzungen, Schäden, Auffälligkeiten …" aria-describedby="events-hint" />
        <p id="events-hint" class="field-hint">Dienste mit Einträgen hier sind in der Übersicht als „Besonderheiten“ markiert.</p>
      </div>
    </section>

    <div class="action-bar">
      <Button type="button" label="Abbrechen" severity="secondary" text @click="$emit('cancel')" />
      <Button type="submit" :label="submitLabel" icon="pi pi-check" :loading="loading" />
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Calendar from 'primevue/calendar'
import Button from 'primevue/button'
import Message from 'primevue/message'
import UserChipSelector from '@/components/servicebook/atoms/UserChipSelector.vue'
import type { ServiceFormData, ServiceDetail } from '@/types/servicebook'
import { useUsersStore } from '@/stores/users'
import { settingsApi } from '@/api/settings'
import type { UserInfo } from '@/types/api'
import type { ServiceSettings } from '@/types/settings'

interface Props {
  initialData?: ServiceDetail | null
  loading?: boolean
  submitLabel?: string
}

interface Emits {
  (e: 'submit', data: ServiceFormData): void
  (e: 'cancel'): void
}

const props = withDefaults(defineProps<Props>(), {
  initialData: null,
  loading: false,
  submitLabel: 'Speichern'
})

const emit = defineEmits<Emits>()

const usersStore = useUsersStore()

const formData = ref<{
  start: Date | null
  end: Date | null
  topic: string
  place: string
  description: string
  events: string
  operations_manager_ids: number[]
}>({
  start: null,
  end: null,
  topic: '',
  place: '',
  description: '',
  events: '',
  operations_manager_ids: []
})

const errors = ref<Record<string, string>>({})
const usersLoading = ref(false)
const appSettings = ref<ServiceSettings | null>(null)
const serverTimeDiffMinutes = ref<number | null>(null)

const serverTimeDivergent = computed(() => {
  return serverTimeDiffMinutes.value !== null && Math.abs(serverTimeDiffMinutes.value) >= 5
})

const usersOptions = computed(() => {
  const options = usersStore.users.map((user: UserInfo) => ({
    label: user.full_name || user.username,
    value: user.id
  }))
  // Keep already assigned leads visible by name even if their account was deactivated since.
  const known = new Set(options.map((option) => option.value))
  for (const manager of props.initialData?.operations_manager ?? []) {
    if (!known.has(manager.id)) options.push({ label: `${manager.full_name || manager.username} (inaktiv)`, value: manager.id })
  }
  return options
})

/**
 * Set form dates to today with default times from settings
 */
const setTodayWithDefaultTime = async () => {
  try {
    // Load settings if not already loaded
    if (!appSettings.value) {
      const response = await settingsApi.getService()
      appSettings.value = response.data
    }

    const today = new Date()
    
    // Parse default start time (format: "HH:mm")
    const startTimeParts = appSettings.value.service_start_time.split(':').map(Number)
    const startHour = startTimeParts[0] ?? 19
    const startMinute = startTimeParts[1] ?? 0
    const startDate = new Date(today)
    startDate.setHours(startHour, startMinute, 0, 0)
    
    // Parse default end time (format: "HH:mm")
    const endTimeParts = appSettings.value.service_end_time.split(':').map(Number)
    const endHour = endTimeParts[0] ?? 21
    const endMinute = endTimeParts[1] ?? 0
    const endDate = new Date(today)
    endDate.setHours(endHour, endMinute, 0, 0)
    
    formData.value.start = startDate
    formData.value.end = endDate
  } catch {
    // Fallback to default times if settings load fails
    const today = new Date()
    const startDate = new Date(today)
    startDate.setHours(19, 0, 0, 0)
    const endDate = new Date(today)
    endDate.setHours(21, 0, 0, 0)
    
    formData.value.start = startDate
    formData.value.end = endDate
  }
}

// Load users and settings on mount
onMounted(async () => {
  usersLoading.value = true
  try {
    await Promise.all([
      usersStore.fetchUsers({ limit: 1000, is_active: true }),
      settingsApi.getService().then(response => {
        appSettings.value = response.data
        // Detect server/client time divergence via Date response header
        const dateHeader = response.headers['date']
        if (dateHeader) {
          const serverTime = new Date(dateHeader)
          const clientTime = new Date()
          const diffMs = serverTime.getTime() - clientTime.getTime()
          serverTimeDiffMinutes.value = Math.round(diffMs / 60000)
        }
      })
    ])
  } catch {
  } finally {
    usersLoading.value = false
  }
})

// Watch for initial data changes
watch(
  () => props.initialData,
  (newData) => {
    if (newData) {
      formData.value = {
        start: newData.start ? new Date(newData.start) : null,
        end: newData.end ? new Date(newData.end) : null,
        topic: newData.topic || '',
        place: newData.place || '',
        description: newData.description || '',
        events: newData.events || '',
        operations_manager_ids: newData.operations_manager?.map((m) => m.id) || []
      }
    }
  },
  { immediate: true }
)

const validate = (): boolean => {
  errors.value = {}

  if (!formData.value.start) {
    errors.value.start = 'Startdatum ist erforderlich'
  }

  if (!formData.value.end) {
    errors.value.end = 'Enddatum ist erforderlich'
  }

  if (formData.value.start && formData.value.end && formData.value.end <= formData.value.start) {
    errors.value.end = 'Endzeit muss nach der Startzeit liegen'
  }

  return Object.keys(errors.value).length === 0
}

const handleSubmit = () => {
  if (!validate()) return

  const submitData: ServiceFormData = {
    start: formData.value.start!.toISOString(),
    end: formData.value.end!.toISOString(),
    topic: formData.value.topic || undefined,
    place: formData.value.place || undefined,
    description: formData.value.description || undefined,
    events: formData.value.events || undefined,
    operations_manager_ids: formData.value.operations_manager_ids.length
      ? formData.value.operations_manager_ids
      : undefined
  }

  emit('submit', submitData)
}
</script>

<style scoped>
.service-form {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.form-card {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  padding: var(--jf-space-3);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: var(--jf-shadow-sm);
}

.form-card h2 {
  margin: 0;
  font-size: var(--jf-text-lg);
  font-weight: var(--jf-weight-semibold);
}

.form-card__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--jf-space-2) 20px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.form-field--wide {
  grid-column: 1 / -1;
}

.form-field label,
.field-label {
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text);
}

.field-optional {
  font-weight: 400;
  color: var(--jf-color-text-muted);
}

.form-field :deep(.p-inputtext),
.form-field :deep(.p-datepicker),
.form-field :deep(.p-textarea) {
  width: 100%;
}

.field-error {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 0.8125rem;
  font-weight: var(--jf-weight-semibold);
  color: var(--p-red-700);
}

.app-dark .field-error {
  color: var(--p-red-300);
}

.field-hint {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.action-bar {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  justify-content: flex-end;
  gap: var(--jf-space-1);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: 0 -4px 12px rgba(23, 32, 51, 0.06);
}

@media (max-width: 1023px) {
  .action-bar {
    bottom: calc(64px + env(safe-area-inset-bottom, 0px));
  }
}

@media (max-width: 767px) {
  .form-card {
    padding: var(--jf-space-2);
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .action-bar :deep(.p-button:last-child) {
    flex: 1;
  }
}
</style>
