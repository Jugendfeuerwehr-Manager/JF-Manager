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
        <h2 class="settings-section__title">OIDC / SSO</h2>
        <p class="settings-section__description">Single Sign-On via OpenID Connect</p>
      </div>
    </div>
    <OidcSettingsForm
      :settings="settingsStore.oidc"
      :can-edit="settingsStore.canChangeCategory('oidc')"
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
import OidcSettingsForm from '../../molecules/OidcSettingsForm.vue'
import type { OIDCSettings } from '@/types/oidc'
import { useMobile } from '@/composables/useMobile'

const settingsStore = useSettingsStore()
const toast = useToast()
const router = useRouter()
const { isMobile } = useMobile()

onMounted(async () => {
  if (!settingsStore.oidc) {
    try {
      await settingsStore.fetchCategorySettings('oidc')
    } catch {
      toast.add({ severity: 'error', summary: 'Fehler', detail: 'Einstellungen konnten nicht geladen werden', life: 5000 })
    }
  }
})

async function handleSave(data: Partial<OIDCSettings>) {
  try {
    await settingsStore.updateOidc(data)
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'OIDC Einstellungen gespeichert', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Fehler beim Speichern', life: 5000 })
  }
}
</script>
