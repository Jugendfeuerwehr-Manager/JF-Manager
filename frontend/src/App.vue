<script setup lang="ts">
import { watch } from 'vue'
import { RouterView } from 'vue-router'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import { useAppSettings } from '@/composables/useAppSettings'

const { websiteTitle, setDocumentTitle } = useAppSettings()

// Update document title when website title changes
watch(websiteTitle, () => {
  setDocumentTitle()
}, { immediate: true })
</script>

<template>
  <Toast />
  <ConfirmDialog />
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
