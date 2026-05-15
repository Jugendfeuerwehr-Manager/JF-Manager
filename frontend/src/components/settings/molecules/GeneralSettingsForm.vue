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
        help-text="Der Titel der Website, der im Browser-Tab und auf der Loginseite angezeigt wird"
        :disabled="!canEdit"
      />
      <SettingsTextField
        v-model="formData.slug"
        label="Organisations-Kürzel"
        field-id="slug"
        help-text="Kurzbezeichnung der Organisation (z.B. 'JF Berlin'). Wird auf der Loginseite angezeigt."
        :disabled="!canEdit"
      />
      <SettingsTextField
        v-model="formData.logo_url"
        label="Logo URL"
        field-id="logo_url"
        help-text="Öffentlich erreichbare URL zum Logo der Organisation. Wird auf der Loginseite angezeigt."
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
  title: '',
  slug: '',
  logo_url: ''
})

const originalData = ref<GeneralSettings | null>(null)
const successMessage = ref('')

// Watch for settings changes from parent
watch(() => props.settings, (newSettings) => {
  if (newSettings) {
    formData.title = newSettings.title || ''
    formData.slug = newSettings.slug || ''
    formData.logo_url = newSettings.logo_url || ''
    originalData.value = { ...newSettings }
  }
}, { immediate: true })

const hasChanges = computed(() => {
  if (!originalData.value) return false
  return (
    formData.title !== originalData.value.title ||
    formData.slug !== originalData.value.slug ||
    formData.logo_url !== originalData.value.logo_url
  )
})

function handleSubmit() {
  const changes: Partial<GeneralSettings> = {}
  
  if (formData.title !== originalData.value?.title) {
    changes.title = formData.title
  }
  if (formData.slug !== originalData.value?.slug) {
    changes.slug = formData.slug
  }
  if (formData.logo_url !== originalData.value?.logo_url) {
    changes.logo_url = formData.logo_url
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
    formData.slug = originalData.value.slug || ''
    formData.logo_url = originalData.value.logo_url || ''
  }
}
</script>
