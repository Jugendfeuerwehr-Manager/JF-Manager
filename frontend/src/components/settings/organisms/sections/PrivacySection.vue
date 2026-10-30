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
        <h2 class="settings-section__title">Datenschutz</h2>
        <p class="settings-section__description">Impressum und Datenschutzerklärung pflegen und veröffentlichen</p>
      </div>
    </div>

    <Message v-if="privacyStore.legalError" severity="error" :closable="false">{{ privacyStore.legalError }}</Message>
    <ProgressSpinner v-if="privacyStore.legalLoading && !privacyStore.legalPages.length" />
    <Tabs v-else v-model:value="activeKind">
      <TabList>
        <Tab v-for="page in privacyStore.legalPages" :key="page.kind" :value="page.kind">{{ page.label }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel v-for="page in privacyStore.legalPages" :key="page.kind" :value="page.kind">
          <LegalPageEditor
            :page="page"
            :versions="privacyStore.versions[page.kind] ?? []"
            :can-edit="settingsStore.canChangeCategory('privacy')"
            :saving="privacyStore.legalSaving"
            @save="data => handleSave(page.kind, data)"
            @publish="data => handlePublish(page.kind, data)"
          />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import LegalPageEditor from '@/components/privacy/organisms/LegalPageEditor.vue'
import { useMobile } from '@/composables/useMobile'
import { usePrivacyStore } from '@/stores/privacy'
import { useSettingsStore } from '@/stores/settings'
import type { LegalPageKind } from '@/types/privacy'

const privacyStore = usePrivacyStore()
const settingsStore = useSettingsStore()
const toast = useToast()
const router = useRouter()
const { isMobile } = useMobile()
const activeKind = ref<LegalPageKind>('imprint')

onMounted(async () => {
  await privacyStore.fetchLegalPages()
  await privacyStore.fetchVersions(activeKind.value)
})

watch(activeKind, kind => {
  if (!privacyStore.versions[kind]) void privacyStore.fetchVersions(kind)
})

async function handleSave(kind: LegalPageKind, data: { draft_title: string, draft_body: string }) {
  if (await privacyStore.saveDraft(kind, data)) {
    toast.add({ severity: 'success', summary: 'Gespeichert', detail: 'Entwurf gespeichert', life: 3000 })
  }
}

async function handlePublish(kind: LegalPageKind, data: { draft_title: string, draft_body: string, change_note: string }) {
  // Publishing always freezes what the editor shows, so save the draft first.
  if (!(await privacyStore.saveDraft(kind, { draft_title: data.draft_title, draft_body: data.draft_body }))) return
  if (await privacyStore.publish(kind, data.change_note)) {
    toast.add({ severity: 'success', summary: 'Veröffentlicht', detail: 'Neue Version ist öffentlich', life: 3000 })
  }
}
</script>
