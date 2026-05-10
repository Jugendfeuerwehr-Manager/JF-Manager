<template>
  <div class="settings-view">
    <div class="mb-4">
      <h1 class="text-3xl font-bold">Einstellungen</h1>
      <p class="text-color-secondary">Verwalten Sie die Anwendungseinstellungen</p>
    </div>

    <!-- Loading State -->
    <div v-if="settingsStore.loading && !hasAnySettings" class="flex justify-content-center align-items-center" style="min-height: 400px;">
      <ProgressSpinner />
    </div>

    <!-- Error State -->
    <Message v-else-if="settingsStore.error && !hasAnySettings" severity="error" :closable="true" @close="settingsStore.clearError()">
      {{ settingsStore.error }}
    </Message>

    <!-- No Permission State -->
    <Message v-else-if="!settingsStore.canViewAnySettings" severity="warn" :closable="false">
      Sie haben keine Berechtigung, Einstellungen anzuzeigen.
    </Message>

    <!-- Settings Tabs -->
    <TabView v-else-if="settingsStore.availableTabs.length > 0" :activeIndex="activeTabIndex" @tab-change="onTabChange">
      <TabPanel
        v-for="(tab, index) in settingsStore.availableTabs"
        :key="tab.id"
        :value="index"
      >
        <template #header>
          <div class="flex align-items-center gap-2">
            <i :class="tab.icon"></i>
            <span>{{ tab.title }}</span>
          </div>
        </template>

        <!-- General Settings -->
        <GeneralSettingsForm
          v-if="tab.id === 'general'"
          :settings="settingsStore.general"
          :can-edit="settingsStore.canChangeCategory('general')"
          :saving="settingsStore.loading"
          @save="handleSaveGeneral"
        />

        <!-- Email Settings -->
        <EmailSettingsForm
          v-else-if="tab.id === 'email'"
          :settings="settingsStore.email"
          :can-edit="settingsStore.canChangeCategory('email')"
          :saving="settingsStore.loading"
          @save="handleSaveEmail"
        />

        <!-- Member Settings -->
        <div v-else-if="tab.id === 'member'" class="flex flex-column gap-4">
          <MemberSettingsForm
            :settings="settingsStore.member"
            :can-edit="settingsStore.canChangeCategory('member')"
            :saving="settingsStore.loading"
            @save="handleSaveMember"
          />
          <MemberSyncJobsCard :can-edit="settingsStore.canChangeCategory('member')" />
          <StatusesManager :can-edit="settingsStore.canChangeCategory('member')" />
          <EventTypesManager :can-edit="settingsStore.canChangeCategory('member')" />
        </div>

        <!-- Service Settings -->
        <ServiceSettingsForm
          v-else-if="tab.id === 'service'"
          :settings="settingsStore.service"
          :can-edit="settingsStore.canChangeCategory('service')"
          :saving="settingsStore.loading"
          @save="handleSaveService"
        />

        <!-- Order Settings -->
        <OrderSettingsForm
          v-else-if="tab.id === 'order'"
          :settings="settingsStore.order"
          :can-edit="settingsStore.canChangeCategory('order')"
          :saving="settingsStore.loading"
          @save="handleSaveOrder"
        />

        <!-- LDAP Settings -->
        <LdapSettingsForm
          v-else-if="tab.id === 'ldap'"
          :settings="settingsStore.ldap"
          :can-edit="settingsStore.canChangeCategory('ldap')"
          :saving="settingsStore.loading"
          @save="handleSaveLdap"
        />

        <!-- OIDC / SSO Settings -->
        <OidcSettingsForm
          v-else-if="tab.id === 'oidc'"
          :settings="settingsStore.oidc"
          :can-edit="settingsStore.canChangeCategory('oidc')"
          :saving="settingsStore.loading"
          @save="handleSaveOidc"
        />

        <!-- Email Templates -->
        <EmailTemplatesView
          v-else-if="tab.id === 'email-templates'"
        />
      </TabPanel>
    </TabView>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import { useSettingsStore } from '@/stores/settings'
import GeneralSettingsForm from '../molecules/GeneralSettingsForm.vue'
import EmailSettingsForm from '../molecules/EmailSettingsForm.vue'
import MemberSettingsForm from '../molecules/MemberSettingsForm.vue'
import MemberSyncJobsCard from '../molecules/MemberSyncJobsCard.vue'
import ServiceSettingsForm from '../molecules/ServiceSettingsForm.vue'
import OrderSettingsForm from '../molecules/OrderSettingsForm.vue'
import LdapSettingsForm from '../molecules/LdapSettingsForm.vue'
import OidcSettingsForm from '../molecules/OidcSettingsForm.vue'
import StatusesManager from '../molecules/StatusesManager.vue'
import EventTypesManager from '../molecules/EventTypesManager.vue'
import EmailTemplatesView from './EmailTemplatesView.vue'
import type {
  GeneralSettings,
  EmailSettings,
  MemberSettings,
  ServiceSettings,
  OrderSettings,
  LdapSettings
} from '@/types/settings'
import type { OIDCSettings } from '@/types/oidc'

const settingsStore = useSettingsStore()
const toast = useToast()
const activeTabIndex = ref(0)

const hasAnySettings = computed(() => {
  return !!(
    settingsStore.general ||
    settingsStore.email ||
    settingsStore.member ||
    settingsStore.service ||
    settingsStore.order ||
    settingsStore.ldap ||
    settingsStore.oidc
  )
})

onMounted(async () => {
  try {
    // Fetch permissions first
    await settingsStore.fetchPermissions()
    
    // Then fetch all settings the user can access
    if (settingsStore.canViewAnySettings) {
      await settingsStore.fetchAllSettings()
    }
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Fehler beim Laden der Einstellungen',
      life: 5000
    })
  }
})

function onTabChange(event: { index: number }) {
  activeTabIndex.value = event.index
}

async function handleSaveGeneral(data: Partial<GeneralSettings>) {
  try {
    await settingsStore.updateGeneral(data)
    toast.add({
      severity: 'success',
      summary: 'Erfolgreich',
      detail: 'Allgemeine Einstellungen gespeichert',
      life: 3000
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Fehler beim Speichern der Einstellungen',
      life: 5000
    })
  }
}

async function handleSaveEmail(data: Partial<EmailSettings>) {
  try {
    await settingsStore.updateEmail(data)
    toast.add({
      severity: 'success',
      summary: 'Erfolgreich',
      detail: 'E-Mail Einstellungen gespeichert',
      life: 3000
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Fehler beim Speichern der E-Mail Einstellungen',
      life: 5000
    })
  }
}

async function handleSaveMember(data: Partial<MemberSettings>) {
  try {
    await settingsStore.updateMember(data)
    toast.add({
      severity: 'success',
      summary: 'Erfolgreich',
      detail: 'Mitglieder Einstellungen gespeichert',
      life: 3000
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Fehler beim Speichern der Mitglieder Einstellungen',
      life: 5000
    })
  }
}

async function handleSaveService(data: Partial<ServiceSettings>) {
  try {
    await settingsStore.updateService(data)
    toast.add({
      severity: 'success',
      summary: 'Erfolgreich',
      detail: 'Dienst Einstellungen gespeichert',
      life: 3000
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Fehler beim Speichern der Dienst Einstellungen',
      life: 5000
    })
  }
}

async function handleSaveOrder(data: Partial<OrderSettings>) {
  try {
    await settingsStore.updateOrder(data)
    toast.add({
      severity: 'success',
      summary: 'Erfolgreich',
      detail: 'Bestellungs Einstellungen gespeichert',
      life: 3000
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Fehler beim Speichern der Bestellungs Einstellungen',
      life: 5000
    })
  }
}

async function handleSaveLdap(data: Partial<LdapSettings>) {
  try {
    await settingsStore.updateLdap(data)
    toast.add({
      severity: 'success',
      summary: 'Erfolgreich',
      detail: 'LDAP Einstellungen gespeichert',
      life: 3000
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Fehler beim Speichern der LDAP Einstellungen',
      life: 5000
    })
  }
}

async function handleSaveOidc(data: Partial<OIDCSettings>) {
  try {
    await settingsStore.updateOidc(data)
    toast.add({
      severity: 'success',
      summary: 'Erfolgreich',
      detail: 'OIDC Einstellungen gespeichert',
      life: 3000
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Fehler beim Speichern der OIDC Einstellungen',
      life: 5000
    })
  }
}


</script>

<style scoped>
.settings-view {
  padding: 1rem;
}
</style>
