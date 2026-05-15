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
        <h2 class="settings-section__title">E-Mail-Vorlagen</h2>
        <p class="settings-section__description">E-Mail-Vorlagen bearbeiten</p>
      </div>
    </div>
    <Tabs value="content">
      <TabList>
        <Tab value="content">Inhaltsvorlagen</Tab>
        <Tab value="layouts">Layout-Vorlagen</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="content">
          <EmailTemplatesView />
        </TabPanel>
        <TabPanel value="layouts">
          <EmailLayoutTemplatesView />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tabs from 'primevue/tabs'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import EmailTemplatesView from '../EmailTemplatesView.vue'
import EmailLayoutTemplatesView from '../EmailLayoutTemplatesView.vue'
import { useMobile } from '@/composables/useMobile'

const router = useRouter()
const { isMobile } = useMobile()
</script>
