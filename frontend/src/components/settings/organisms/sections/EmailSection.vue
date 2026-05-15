<template>
  <div class="settings-section">
    <div class="settings-section__header">
      <Button
        v-if="isMobile"
        icon="pi pi-arrow-left"
        text
        size="small"
        class="settings-section__back"
        label="Einstellungen"
        @click="router.push('/settings')"
      />
      <div>
        <h2 class="settings-section__title">E-Mail</h2>
        <p class="settings-section__description">SMTP Server und E-Mail Konfiguration</p>
      </div>
    </div>
    <EmailSettingsForm
      :settings="settingsStore.email"
      :can-edit="settingsStore.canChangeCategory('email')"
      :saving="settingsStore.loading"
      @save="handleSave"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import { useSettingsStore } from '@/stores/settings'
import EmailSettingsForm from '../../molecules/EmailSettingsForm.vue'
import type { EmailSettings } from '@/types/settings'
import { useMobile } from '@/composables/useMobile'

const settingsStore = useSettingsStore()
const toast = useToast()
const router = useRouter()
const { isMobile } = useMobile()

onMounted(async () => {
  if (!settingsStore.email) {
    try {
      await settingsStore.fetchCategorySettings('email')
    } catch {
      toast.add({ severity: 'error', summary: 'Fehler', detail: 'Einstellungen konnten nicht geladen werden', life: 5000 })
    }
  }
})

async function handleSave(data: Partial<EmailSettings>) {
  try {
    await settingsStore.updateEmail(data)
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'E-Mail Einstellungen gespeichert', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Fehler beim Speichern', life: 5000 })
  }
}
</script>
