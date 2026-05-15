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
        <h2 class="settings-section__title">Mitglieder</h2>
        <p class="settings-section__description">Mitglieder-bezogene Einstellungen</p>
      </div>
    </div>
    <div class="flex flex-column gap-4">
      <MemberSettingsForm
        :settings="settingsStore.member"
        :can-edit="settingsStore.canChangeCategory('member')"
        :saving="settingsStore.loading"
        @save="handleSave"
      />
      <MemberSyncJobsCard :can-edit="settingsStore.canChangeCategory('member')" />
      <StatusesManager :can-edit="settingsStore.canChangeCategory('member')" />
      <EventTypesManager :can-edit="settingsStore.canChangeCategory('member')" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import { useSettingsStore } from '@/stores/settings'
import MemberSettingsForm from '../../molecules/MemberSettingsForm.vue'
import MemberSyncJobsCard from '../../molecules/MemberSyncJobsCard.vue'
import StatusesManager from '../../molecules/StatusesManager.vue'
import EventTypesManager from '../../molecules/EventTypesManager.vue'
import type { MemberSettings } from '@/types/settings'
import { useMobile } from '@/composables/useMobile'

const settingsStore = useSettingsStore()
const toast = useToast()
const router = useRouter()
const { isMobile } = useMobile()

onMounted(async () => {
  if (!settingsStore.member) {
    try {
      await settingsStore.fetchCategorySettings('member')
    } catch {
      toast.add({ severity: 'error', summary: 'Fehler', detail: 'Einstellungen konnten nicht geladen werden', life: 5000 })
    }
  }
})

async function handleSave(data: Partial<MemberSettings>) {
  try {
    await settingsStore.updateMember(data)
    toast.add({ severity: 'success', summary: 'Erfolgreich', detail: 'Mitglieder Einstellungen gespeichert', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Fehler beim Speichern', life: 5000 })
  }
}
</script>
