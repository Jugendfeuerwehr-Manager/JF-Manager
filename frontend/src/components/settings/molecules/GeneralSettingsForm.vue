<template>
  <SettingsCategoryCard
    title="Allgemeine Einstellungen"
    description="Grundlegende Anwendungseinstellungen"
    icon="pi pi-cog"
  >
    <form @submit.prevent="handleSubmit">
      <SettingsTextField
        v-model="formData.title"
        label="Website Titel"
        field-id="title"
        help-text="Der Titel der Website, der im Browser-Tab angezeigt wird"
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
import type { GeneralSettings } from '@/types/settings'

interface Props {
  settings: GeneralSettings | null
  canEdit: boolean
  saving?: boolean
}

interface Emits {
  (e: 'save', data: Partial<GeneralSettings>): void
}

const props = withDefaults(defineProps<Props>(), {
  saving: false
})
const emit = defineEmits<Emits>()

const formData = reactive<GeneralSettings>({
  title: ''
})

const originalData = ref<GeneralSettings | null>(null)
const successMessage = ref('')

// Watch for settings changes from parent
watch(() => props.settings, (newSettings) => {
  if (newSettings) {
    formData.title = newSettings.title || ''
    originalData.value = { ...newSettings }
  }
}, { immediate: true })

const hasChanges = computed(() => {
  if (!originalData.value) return false
  return formData.title !== originalData.value.title
})

function handleSubmit() {
  const changes: Partial<GeneralSettings> = {}
  
  if (formData.title !== originalData.value?.title) {
    changes.title = formData.title
  }
  
  if (Object.keys(changes).length > 0) {
    emit('save', changes)
    successMessage.value = 'Einstellungen erfolgreich gespeichert'
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  }
}

function handleCancel() {
  if (originalData.value) {
    formData.title = originalData.value.title || ''
  }
}
</script>
