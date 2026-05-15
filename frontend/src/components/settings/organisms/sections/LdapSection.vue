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
        <h2 class="settings-section__title">LDAP</h2>
        <p class="settings-section__description">LDAP Anmeldung und Gruppen-Synchronisation</p>
      </div>
    </div>
    <LdapSettingsForm
      :settings="settingsStore.ldap"
      :can-edit="settingsStore.canChangeCategory('ldap')"
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
import LdapSettingsForm from '../../molecules/LdapSettingsForm.vue'
import type { LdapSettings } from '@/types/settings'
import { useMobile } from '@/composables/useMobile'

const settingsStore = useSettingsStore()
const toast = useToast()
const router = useRouter()
const { isMobile } = useMobile()

onMounted(async () => {
  if (!settingsStore.ldap) {
    try {
      await settingsStore.fetchCategorySettings('ldap')
    } catch {
      toast.add({ severity: 'error', summary: 'Fehler', detail: 'Einstellungen konnten nicht geladen werden', life: 5000 })
    }
  }
})

async function handleSave(data: Partial<LdapSettings>) {
  try {
    await settingsStore.updateLdap(data)
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'LDAP Einstellungen gespeichert', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Fehler beim Speichern', life: 5000 })
  }
}
</script>
