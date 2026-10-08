<script setup lang="ts">
import { watch } from 'vue'
import { RouterView } from 'vue-router'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import { useAppSettings } from '@/composables/useAppSettings'

import { useAuthStore } from '@/stores/auth'
import { disableDevicePush } from '@/utils/pwa'
import StepUpDialog from '@/components/security/StepUpDialog.vue'

const auth = useAuthStore()
watch(() => auth.isAuthenticated, (authenticated) => {
  if (!authenticated) void disableDevicePush().catch(() => {})
}, { immediate: true })

const { websiteTitle, setDocumentTitle } = useAppSettings()

// Update document title when website title changes
watch(websiteTitle, () => {
  setDocumentTitle()
}, { immediate: true })
</script>

<template>
  <Toast />
  <ConfirmDialog />
  <StepUpDialog v-if="auth.isAuthenticated" />
  <RouterView />
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-family);
  background: var(--p-surface-ground);
  color: var(--p-text-color);
}

#app {
  min-height: 100vh;
}
</style>
