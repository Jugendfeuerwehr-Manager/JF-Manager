<template>
  <SettingsCategoryCard
    title="E-Mail Einstellungen"
    description="SMTP Server und E-Mail Konfiguration"
    icon="pi pi-envelope"
  >
    <form @submit.prevent="handleSubmit">
      <div class="grid">
        <div class="col-12 md:col-8">
          <SettingsTextField
            v-model="formData.email_host"
            label="SMTP Server"
            field-id="email_host"
            placeholder="smtp.gmail.com"
            help-text="Hostname oder IP-Adresse des SMTP-Servers"
            :disabled="!canEdit"
          />
        </div>
        <div class="col-12 md:col-4">
          <SettingsNumberField
            v-model="formData.email_port"
            label="SMTP Port"
            field-id="email_port"
            :min="1"
            :max="65535"
            help-text="Port des SMTP-Servers"
            :disabled="!canEdit"
          />
        </div>
      </div>

      <div class="grid">
        <div class="col-12 md:col-6">
          <SettingsCheckbox
            v-model="formData.email_use_tls"
            label="TLS verwenden"
            field-id="email_use_tls"
            help-text="TLS-Verschlüsselung für die E-Mail-Verbindung"
            :disabled="!canEdit"
          />
        </div>
        <div class="col-12 md:col-6">
          <SettingsCheckbox
            v-model="formData.email_use_ssl"
            label="SSL verwenden"
            field-id="email_use_ssl"
            help-text="SSL-Verschlüsselung (nicht zusammen mit TLS)"
            :disabled="!canEdit"
          />
        </div>
      </div>

      <SettingsTextField
        v-model="formData.email_host_user"
        label="SMTP Benutzername"
        field-id="email_host_user"
        help-text="Benutzername für die Authentifizierung beim SMTP-Server"
        :disabled="!canEdit"
      />

      <SettingsTextField
        v-model="formData.email_host_password"
        label="SMTP Passwort"
        field-id="email_host_password"
        help-text="Passwort für die Authentifizierung beim SMTP-Server"
        :disabled="!canEdit"
      />

      <SettingsTextField
        v-model="formData.default_from_email"
        label="Absender E-Mail"
        field-id="default_from_email"
        placeholder="noreply@example.com"
        help-text="E-Mail-Adresse, die als Absender verwendet wird"
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
import SettingsCategoryCard from '../atoms/SettingsCategoryCard.vue'
import SettingsTextField from '../atoms/SettingsTextField.vue'
import SettingsNumberField from '../atoms/SettingsNumberField.vue'
import SettingsCheckbox from '../atoms/SettingsCheckbox.vue'
import type { EmailSettings } from '@/types/settings'

interface Props {
  settings: EmailSettings | null
  canEdit: boolean
  saving?: boolean
}

interface Emits {
  (e: 'save', data: Partial<EmailSettings>): void
}

const props = withDefaults(defineProps<Props>(), {
  saving: false
})
const emit = defineEmits<Emits>()

const formData = reactive<EmailSettings & { email_host_password: string }>({
  email_host: '',
  email_port: 587,
  email_use_tls: true,
  email_use_ssl: false,
  email_host_user: '',
  email_host_password: '',
  default_from_email: ''
})

const originalData = ref<EmailSettings | null>(null)
const successMessage = ref('')
const errorMessage = ref('')

watch(() => props.settings, (newSettings) => {
  if (newSettings) {
    formData.email_host = newSettings.email_host || ''
    formData.email_port = newSettings.email_port || 587
    formData.email_use_tls = newSettings.email_use_tls ?? true
    formData.email_use_ssl = newSettings.email_use_ssl ?? false
    formData.email_host_user = newSettings.email_host_user || ''
    formData.email_host_password = newSettings.email_host_password || ''
    formData.default_from_email = newSettings.default_from_email || ''
    originalData.value = { ...newSettings }
  }
}, { immediate: true })

const hasChanges = computed(() => {
  if (!originalData.value) return false
  return (
    formData.email_host !== originalData.value.email_host ||
    formData.email_port !== originalData.value.email_port ||
    formData.email_use_tls !== originalData.value.email_use_tls ||
    formData.email_use_ssl !== originalData.value.email_use_ssl ||
    formData.email_host_user !== originalData.value.email_host_user ||
    formData.email_host_password !== originalData.value.email_host_password ||
    formData.default_from_email !== originalData.value.default_from_email
  )
})

function handleSubmit() {
  // Validate TLS/SSL
  if (formData.email_use_tls && formData.email_use_ssl) {
    errorMessage.value = 'TLS und SSL können nicht gleichzeitig aktiviert sein'
    return
  }

  const changes: Partial<EmailSettings> = {}
  
  if (formData.email_host !== originalData.value?.email_host) {
    changes.email_host = formData.email_host
  }
  if (formData.email_port !== originalData.value?.email_port) {
    changes.email_port = formData.email_port
  }
  if (formData.email_use_tls !== originalData.value?.email_use_tls) {
    changes.email_use_tls = formData.email_use_tls
  }
  if (formData.email_use_ssl !== originalData.value?.email_use_ssl) {
    changes.email_use_ssl = formData.email_use_ssl
  }
  if (formData.email_host_user !== originalData.value?.email_host_user) {
    changes.email_host_user = formData.email_host_user
  }
  if (formData.email_host_password !== originalData.value?.email_host_password) {
    changes.email_host_password = formData.email_host_password
  }
  if (formData.default_from_email !== originalData.value?.default_from_email) {
    changes.default_from_email = formData.default_from_email
  }
  
  if (Object.keys(changes).length > 0) {
    emit('save', changes)
    successMessage.value = 'E-Mail Einstellungen erfolgreich gespeichert'
    errorMessage.value = ''
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  }
}

function handleCancel() {
  if (originalData.value) {
    formData.email_host = originalData.value.email_host || ''
    formData.email_port = originalData.value.email_port || 587
    formData.email_use_tls = originalData.value.email_use_tls ?? true
    formData.email_use_ssl = originalData.value.email_use_ssl ?? false
    formData.email_host_user = originalData.value.email_host_user || ''
    formData.email_host_password = originalData.value.email_host_password || ''
    formData.default_from_email = originalData.value.default_from_email || ''
  }
  errorMessage.value = ''
}
</script>
