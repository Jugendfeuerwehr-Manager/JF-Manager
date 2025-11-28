<template>
  <SettingsCategoryCard
    title="Dienst Einstellungen"
    description="Standard-Dienstzeiten und -einstellungen"
    icon="pi pi-calendar"
  >
    <form @submit.prevent="handleSubmit">
      <div class="grid">
        <div class="col-12 md:col-6">
          <div class="field">
            <label for="service_start_time" class="block mb-2">Standard Start Zeit</label>
            <Calendar
              id="service_start_time"
              v-model="formData.service_start_time"
              :timeOnly="true"
              :disabled="!canEdit"
              updateModelType="replace"
              class="w-full"
            />
            <small class="text-color-secondary">Standard-Startzeit für neue Dienste</small>
          </div>
        </div>
        <div class="col-12 md:col-6">
            <label for="service_end_time" class="block mb-2">Standard Ende Zeit</label>
            <Calendar
              id="service_end_time"
              v-model="formData.service_end_time"
              :timeOnly="true"
              :disabled="!canEdit"
              updateModelType="replace"
              class="w-full"
            />
            <small class="text-color-secondary">Standard-Endzeit für neue Dienste</small>
            <small class="text-color-secondary">Standard-Endzeit für neue Dienste</small>
          </div>
        </div>

      <div class="flex justify-content-end gap-2 mt-4">
        <Button
          label="Abbrechen"
          severity="secondary"
          @click="handleCancel"
          :disabled="!hasChanges"
        />
        <Button
          label="Speichern"
          type="submit"
          :loading="saving"
          :disabled="!canEdit || !hasChanges"
        />
      </div>
    </form>

    <template #footer v-if="successMessage || errorMessage">
      <Message v-if="successMessage" severity="success" :closable="false">{{ successMessage }}</Message>
      <Message v-if="errorMessage" severity="error" :closable="true" @close="errorMessage = ''">{{ errorMessage }}</Message>
    </template>
  </SettingsCategoryCard>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Calendar from 'primevue/calendar'
import SettingsCategoryCard from '../atoms/SettingsCategoryCard.vue'
import type { ServiceSettings } from '@/types/settings'

interface Props {
  settings: ServiceSettings | null
  canEdit: boolean
  saving?: boolean
}

interface Emits {
  (e: 'save', data: Partial<ServiceSettings>): void
}

const props = withDefaults(defineProps<Props>(), {
  saving: false
})
const emit = defineEmits<Emits>()

const formData = reactive<{
  service_start_time: Date | null
  service_end_time: Date | null
}>({
  service_start_time: null,
  service_end_time: null
})

const originalData = ref<ServiceSettings | null>(null)
const successMessage = ref('')
const errorMessage = ref('')

// Helper to parse time string "HH:MM" to Date
function parseTime(timeStr: string): Date | null {
  if (!timeStr) return null
  const parts = timeStr.split(':')
  if (parts.length !== 2 || !parts[0] || !parts[1]) return null
  const hours = parseInt(parts[0], 10)
  const minutes = parseInt(parts[1], 10)
  if (isNaN(hours) || isNaN(minutes)) return null
  const date = new Date()
  date.setHours(hours, minutes, 0, 0)
  return date
}

// Helper to format Date to "HH:MM"
function formatTime(date: Date | null): string {
  if (!date) return ''
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${hours}:${minutes}`
}

watch(() => props.settings, (newSettings) => {
  if (newSettings) {
    formData.service_start_time = parseTime(newSettings.service_start_time)
    formData.service_end_time = parseTime(newSettings.service_end_time)
    originalData.value = { ...newSettings }
  }
}, { immediate: true })

const hasChanges = computed(() => {
  if (!originalData.value) return false
  const currentStart = formatTime(formData.service_start_time)
  const currentEnd = formatTime(formData.service_end_time)
  return (
    currentStart !== originalData.value.service_start_time ||
    currentEnd !== originalData.value.service_end_time
  )
})

function handleSubmit() {
  // Validate times
  if (formData.service_start_time && formData.service_end_time) {
    if (formData.service_start_time >= formData.service_end_time) {
      errorMessage.value = 'Die Startzeit muss vor der Endzeit liegen'
      return
    }
  }

  const changes: Partial<ServiceSettings> = {}
  const currentStart = formatTime(formData.service_start_time)
  const currentEnd = formatTime(formData.service_end_time)
  
  if (currentStart !== originalData.value?.service_start_time) {
    changes.service_start_time = currentStart
  }
  if (currentEnd !== originalData.value?.service_end_time) {
    changes.service_end_time = currentEnd
  }
  
  if (Object.keys(changes).length > 0) {
    emit('save', changes)
    successMessage.value = 'Dienst Einstellungen erfolgreich gespeichert'
    errorMessage.value = ''
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  }
}

function handleCancel() {
  if (originalData.value) {
    formData.service_start_time = parseTime(originalData.value.service_start_time)
    formData.service_end_time = parseTime(originalData.value.service_end_time)
  }
  errorMessage.value = ''
}
</script>
