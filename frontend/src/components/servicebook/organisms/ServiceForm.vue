<template>
  <form @submit.prevent="handleSubmit" class="service-form">
    <!-- Quick Action Button -->
    <div class="form-actions-top mb-3">
      <Button
        type="button"
        label="Heute zu Standard Zeit"
        icon="pi pi-clock"
        severity="secondary"
        outlined
        @click="setTodayWithDefaultTime"
        :disabled="loading"
      />
    </div>

    <div class="form-grid">
      <!-- Start Date/Time -->
      <div class="form-field">
        <label for="start" class="required">Start</label>
        <Calendar
          id="start"
          v-model="formData.start"
          updateModelType="date"
          showTime
          hourFormat="24"
          dateFormat="dd.mm.yy"
          showIcon
          :showButtonBar="true"
          :class="{ 'p-invalid': errors.start }"
        />
        <small v-if="errors.start" class="p-error">{{ errors.start }}</small>
      </div>

      <!-- End Date/Time -->
      <div class="form-field">
        <label for="end" class="required">Ende</label>
        <Calendar
          id="end"
          v-model="formData.end"
          updateModelType="date"
          showTime
          hourFormat="24"
          dateFormat="dd.mm.yy"
          showIcon
          :showButtonBar="true"
          :class="{ 'p-invalid': errors.end }"
        />
        <small v-if="errors.end" class="p-error">{{ errors.end }}</small>
      </div>
       <div class="form-field full-width">
          <Button
          type="button"
          label="Standardzeit setzen"
          icon="pi pi-clock"
          severity="secondary"
          outlined
          @click="setTodayWithDefaultTime"
          :disabled="loading"
        />
       </div>

      <!-- Topic -->
      <div class="form-field full-width">
        <label for="topic">Thema</label>
        <InputText
          id="topic"
          v-model="formData.topic"
          placeholder="z.B. Übung: Erste Hilfe"
        />
      </div>

      <!-- Place -->
      <div class="form-field full-width">
        <label for="place">Ort</label>
        <InputText id="place" v-model="formData.place" placeholder="z.B. Feuerwehrhaus" />
      </div>

      <!-- Operations Manager -->
      <div class="form-field full-width">
        <label for="operations_manager">Übungsleitung</label>
        <UserChipSelector
          v-model="formData.operations_manager_ids"
          :options="usersOptions"
          :loading="usersLoading"
          :searchable="true"
        />
      </div>

      <!-- Description -->
      <div class="form-field full-width">
        <label for="description">Beschreibung</label>
        <Textarea
          id="description"
          v-model="formData.description"
          rows="4"
          placeholder="Beschreibung des Dienstes..."
        />
      </div>

      <!-- Special Events -->
      <div class="form-field full-width">
        <label for="events">Besondere Vorkommnisse</label>
        <Textarea
          id="events"
          v-model="formData.events"
          rows="3"
          placeholder="Besondere Vorkommnisse während des Dienstes..."
        />
      </div>
    </div>

    <!-- Actions -->
    <div class="form-actions">
      <Button
        type="button"
        label="Abbrechen"
        severity="secondary"
        outlined
        @click="$emit('cancel')"
      />
      <Button type="submit" :label="submitLabel" icon="pi pi-save" :loading="loading" />
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Calendar from 'primevue/calendar'
import Button from 'primevue/button'
import UserChipSelector from '@/components/servicebook/atoms/UserChipSelector.vue'
import type { ServiceFormData, ServiceDetail } from '@/types/servicebook'
import { useUsersStore } from '@/stores/users'
import { settingsApi } from '@/api/user'
import type { AppSettings, UserInfo } from '@/types/api'

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
const appSettings = ref<AppSettings | null>(null)

const usersOptions = computed(() => {
  return usersStore.users.map((user: UserInfo) => ({
    label: user.full_name || user.username,
    value: user.id
  }))
})

/**
 * Set form dates to today with default times from settings
 */
const setTodayWithDefaultTime = async () => {
  try {
    // Load settings if not already loaded
    if (!appSettings.value) {
      const response = await settingsApi.get()
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
      usersStore.fetchUsers({ limit: 1000 }),
      settingsApi.get().then(response => {
        appSettings.value = response.data
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
  gap: 1.5rem;
}

.form-actions-top {
  display: flex;
  justify-content: flex-start;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--surface-border);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0; /* Allow shrinking below content size */
}

.form-field.full-width {
  grid-column: span 2;
  min-width: 0; /* Allow shrinking below content size */
}

.form-field label {
  font-weight: 500;
  color: var(--text-color);
}

.form-field label.required::after {
  content: ' *';
  color: var(--red-500);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
    min-width: 0;
  }

  .form-field.full-width {
    grid-column: span 1;
    min-width: 0;
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .form-actions button {
    width: 100%;
  }
}
</style>
