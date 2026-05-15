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
        <h2 class="settings-section__title">Dienste</h2>
        <p class="settings-section__description">Standard-Dienstzeiten und -einstellungen</p>
      </div>
    </div>
    <ServiceSettingsForm
      :settings="settingsStore.service"
      :can-edit="settingsStore.canChangeCategory('service')"
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
import ServiceSettingsForm from '../../molecules/ServiceSettingsForm.vue'
import type { ServiceSettings } from '@/types/settings'
import { useMobile } from '@/composables/useMobile'

const settingsStore = useSettingsStore()
const toast = useToast()
const router = useRouter()
const { isMobile } = useMobile()

onMounted(async () => {
  if (!settingsStore.service) {
    try {
      await settingsStore.fetchCategorySettings('service')
    } catch {
      toast.add({ severity: 'error', summary: 'Fehler', detail: 'Einstellungen konnten nicht geladen werden', life: 5000 })
    }
  }
})

async function handleSave(data: Partial<ServiceSettings>) {
  try {
    await settingsStore.updateService(data)
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'Dienst Einstellungen gespeichert', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Fehler beim Speichern', life: 5000 })
  }
}
</script>
