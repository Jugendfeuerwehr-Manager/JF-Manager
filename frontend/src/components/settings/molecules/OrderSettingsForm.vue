<template>
  <SettingsCategoryCard
    title="Bestellungs Einstellungen"
    description="Benachrichtigungen und E-Mail Einstellungen für Bestellungen"
    icon="pi pi-shopping-cart"
  >
    <form @submit.prevent="handleSubmit">
      <SettingsTextField
        v-model="formData.equipment_manager_email"
        label="Gerätewart E-Mail"
        field-id="equipment_manager_email"
        placeholder="geraetewart@example.com"
        help-text="E-Mail-Adresse des Gerätewarts für Bestellübersichten"
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
import SettingsTextField from '../atoms/SettingsTextField.vue'
import type { OrderSettings } from '@/types/settings'

interface Props {
  settings: OrderSettings | null
  canEdit: boolean
  saving?: boolean
}

interface Emits {
  (e: 'save', data: Partial<OrderSettings>): void
}

const props = withDefaults(defineProps<Props>(), {
  saving: false
})
const emit = defineEmits<Emits>()

const formData = reactive<OrderSettings>({
  equipment_manager_email: ''
})

const originalData = ref<OrderSettings | null>(null)
const successMessage = ref('')

watch(() => props.settings, (newSettings) => {
  if (newSettings) {
    formData.equipment_manager_email = newSettings.equipment_manager_email || ''
    originalData.value = { ...newSettings }
  }
}, { immediate: true })

const hasChanges = computed(() => {
  if (!originalData.value) return false
  return formData.equipment_manager_email !== originalData.value.equipment_manager_email
})

function handleSubmit() {
  const changes: Partial<OrderSettings> = {}
  
  if (formData.equipment_manager_email !== originalData.value?.equipment_manager_email) {
    changes.equipment_manager_email = formData.equipment_manager_email
  }
  
  if (Object.keys(changes).length > 0) {
    emit('save', changes)
    successMessage.value = 'Bestellungs Einstellungen erfolgreich gespeichert'
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  }
}

function handleCancel() {
  if (originalData.value) {
    formData.equipment_manager_email = originalData.value.equipment_manager_email || ''
  }
}
</script>
