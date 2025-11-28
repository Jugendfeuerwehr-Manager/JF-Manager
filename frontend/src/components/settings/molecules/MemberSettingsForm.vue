<template>
  <SettingsCategoryCard
    title="Mitglieder Einstellungen"
    description="Einstellungen für Mitgliederverwaltung"
    icon="pi pi-users"
  >
    <form @submit.prevent="handleSubmit">
      <SettingsNumberField
        v-model="formData.alert_threshold"
        label="Alarm: Schwellenwert nicht Anwesend"
        field-id="alert_threshold"
        :min="1"
        help-text="Definiert den Schwellenwert wann ein Ausrufezeichen angezeigt wird"
        :disabled="!canEdit"
      />

      <SettingsNumberField
        v-model="formData.alert_threshold_last_entries"
        label="Alarm: Intervallgröße"
        field-id="alert_threshold_last_entries"
        :min="1"
        help-text="Definiert die Anzahl an Diensten die rückwärtig betrachtet werden"
        :disabled="!canEdit"
      />

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

    <template #footer v-if="successMessage">
      <Message severity="success" :closable="false">{{ successMessage }}</Message>
    </template>
  </SettingsCategoryCard>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import SettingsCategoryCard from '../atoms/SettingsCategoryCard.vue'
import SettingsNumberField from '../atoms/SettingsNumberField.vue'
import type { MemberSettings } from '@/types/settings'

interface Props {
  settings: MemberSettings | null
  canEdit: boolean
  saving?: boolean
}

interface Emits {
  (e: 'save', data: Partial<MemberSettings>): void
}

const props = withDefaults(defineProps<Props>(), {
  saving: false
})
const emit = defineEmits<Emits>()

const formData = reactive<MemberSettings>({
  alert_threshold: 3,
  alert_threshold_last_entries: 10
})

const originalData = ref<MemberSettings | null>(null)
const successMessage = ref('')

watch(() => props.settings, (newSettings) => {
  if (newSettings) {
    formData.alert_threshold = newSettings.alert_threshold || 3
    formData.alert_threshold_last_entries = newSettings.alert_threshold_last_entries || 10
    originalData.value = { ...newSettings }
  }
}, { immediate: true })

const hasChanges = computed(() => {
  if (!originalData.value) return false
  return (
    formData.alert_threshold !== originalData.value.alert_threshold ||
    formData.alert_threshold_last_entries !== originalData.value.alert_threshold_last_entries
  )
})

function handleSubmit() {
  const changes: Partial<MemberSettings> = {}
  
  if (formData.alert_threshold !== originalData.value?.alert_threshold) {
    changes.alert_threshold = formData.alert_threshold
  }
  if (formData.alert_threshold_last_entries !== originalData.value?.alert_threshold_last_entries) {
    changes.alert_threshold_last_entries = formData.alert_threshold_last_entries
  }
  
  if (Object.keys(changes).length > 0) {
    emit('save', changes)
    successMessage.value = 'Mitglieder Einstellungen erfolgreich gespeichert'
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  }
}

function handleCancel() {
  if (originalData.value) {
    formData.alert_threshold = originalData.value.alert_threshold || 3
    formData.alert_threshold_last_entries = originalData.value.alert_threshold_last_entries || 10
  }
}
</script>
