/**
 * Settings Pinia Store
 * 
 * Manages application settings and preferences
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { settingsApi } from '@/api/user'
import type { AppSettings } from '@/types/api'

export const useSettingsStore = defineStore('settings', () => {
  // State
  const settings = ref<AppSettings | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const appName = computed(() => settings.value?.app_name || 'JF-Manager')
  const organizationName = computed(() => settings.value?.organization_name || '')
  const contactEmail = computed(() => settings.value?.contact_email || '')
  const equipmentManagerEmail = computed(() => settings.value?.equipment_manager_email || '')

  // Actions
  async function fetchSettings() {
    loading.value = true
    error.value = null
    
    try {
      const response = await settingsApi.get()
      settings.value = response.data
      return settings.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch settings'
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function reset() {
    settings.value = null
    loading.value = false
    error.value = null
  }

  return {
    // State
    settings,
    loading,
    error,
    
    // Computed
    appName,
    organizationName,
    contactEmail,
    equipmentManagerEmail,
    
    // Actions
    fetchSettings,
    clearError,
    reset
  }
})
