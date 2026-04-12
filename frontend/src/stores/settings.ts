/**
 * Settings Store
 * Pinia store for managing application settings
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { settingsApi } from '@/api/settings'
import type {
  GeneralSettings,
  EmailSettings,
  MemberSettings,
  ServiceSettings,
  OrderSettings,
  SettingsPermissions,
  SettingsCategory
} from '@/types/settings'

export const useSettingsStore = defineStore('settings', () => {
  // ============================================================================
  // State
  // ============================================================================

  const general = ref<GeneralSettings | null>(null)
  const email = ref<EmailSettings | null>(null)
  const member = ref<MemberSettings | null>(null)
  const service = ref<ServiceSettings | null>(null)
  const order = ref<OrderSettings | null>(null)
  const permissions = ref<SettingsPermissions | null>(null)
  
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ============================================================================
  // Computed
  // ============================================================================

  const hasPermissions = computed(() => permissions.value !== null)
  
  const canViewAnySettings = computed(() => {
    if (!permissions.value) return false
    return permissions.value.can_view_all || 
      Object.values(permissions.value.categories).some(cat => cat.can_view)
  })

  const canChangeAnySettings = computed(() => {
    if (!permissions.value) return false
    return permissions.value.can_change_all || 
      Object.values(permissions.value.categories).some(cat => cat.can_change)
  })

  const canViewCategory = computed(() => (category: SettingsCategory) => {
    if (!permissions.value) return false
    return permissions.value.can_view_all || 
      permissions.value.categories[category]?.can_view || false
  })

  const canChangeCategory = computed(() => (category: SettingsCategory) => {
    if (!permissions.value) return false
    return permissions.value.can_change_all || 
      permissions.value.categories[category]?.can_change || false
  })

  const equipmentManagerEmail = computed(() => order.value?.equipment_manager_email || '')

  const availableTabs = computed(() => {
    if (!permissions.value) return []
    
    const tabs: Array<{ id: SettingsCategory; title: string; icon: string; description: string }> = []
    
    if (canViewCategory.value('general')) {
      tabs.push({
        id: 'general',
        title: 'Allgemein',
        icon: 'pi pi-cog',
        description: 'Allgemeine Anwendungseinstellungen'
      })
    }
    
    if (canViewCategory.value('email')) {
      tabs.push({
        id: 'email',
        title: 'E-Mail',
        icon: 'pi pi-envelope',
        description: 'SMTP Server und E-Mail Konfiguration'
      })
    }
    
    if (canViewCategory.value('member')) {
      tabs.push({
        id: 'member',
        title: 'Mitglieder',
        icon: 'pi pi-users',
        description: 'Mitglieder-bezogene Einstellungen'
      })
    }
    
    if (canViewCategory.value('service')) {
      tabs.push({
        id: 'service',
        title: 'Dienste',
        icon: 'pi pi-calendar',
        description: 'Standard-Dienstzeiten und -einstellungen'
      })
    }
    
    if (canViewCategory.value('order')) {
      tabs.push({
        id: 'order',
        title: 'Bestellungen',
        icon: 'pi pi-shopping-cart',
        description: 'Bestellungs-Benachrichtigungen'
      })
    }
    
    // Email templates tab - check if user can change settings (editing templates)
    if (canChangeCategory.value('email')) {
      tabs.push({
        id: 'email-templates',
        title: 'E-Mail-Vorlagen',
        icon: 'pi pi-envelope',
        description: 'E-Mail-Vorlagen bearbeiten'
      })
    }
    
    return tabs
  })

  // ============================================================================
  // Actions
  // ============================================================================

  /**
   * Fetch user's settings permissions
   */
  async function fetchPermissions() {
    try {
      loading.value = true
      error.value = null
      
      const response = await settingsApi.getPermissions()
      permissions.value = response.data
      
      return permissions.value
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch permissions'
      error.value = errorMessage
      console.error('Error fetching permissions:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch all settings
   */
  async function fetchAllSettings() {
    try {
      loading.value = true
      error.value = null
      
      const response = await settingsApi.getAll()
      const data = response.data
      
      if (data.general) general.value = data.general
      if (data.email) email.value = data.email
      if (data.member) member.value = data.member
      if (data.service) service.value = data.service
      if (data.order) order.value = data.order
      
      return data
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch settings'
      error.value = errorMessage
      console.error('Error fetching settings:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Fetch settings for a specific category
   */
  async function fetchCategorySettings(category: SettingsCategory) {
    try {
      loading.value = true
      error.value = null
      
      const response = await settingsApi.getByCategory(category)
      
      // Update the appropriate ref
      switch (category) {
        case 'general':
          general.value = response.data as GeneralSettings
          break
        case 'email':
          email.value = response.data as EmailSettings
          break
        case 'member':
          member.value = response.data as MemberSettings
          break
        case 'service':
          service.value = response.data as ServiceSettings
          break
        case 'order':
          order.value = response.data as OrderSettings
          break
      }
      
      return response.data
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : `Failed to fetch ${category} settings`
      error.value = errorMessage
      console.error(`Error fetching ${category} settings:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Update settings for a specific category
   */
  async function updateCategorySettings(category: SettingsCategory, data: Record<string, unknown>) {
    try {
      loading.value = true
      error.value = null
      
      const response = await settingsApi.updateByCategory(category, data)
      
      // Update the appropriate ref
      switch (category) {
        case 'general':
          general.value = response.data as GeneralSettings
          break
        case 'email':
          email.value = response.data as EmailSettings
          break
        case 'member':
          member.value = response.data as MemberSettings
          break
        case 'service':
          service.value = response.data as ServiceSettings
          break
        case 'order':
          order.value = response.data as OrderSettings
          break
      }
      
      return response.data
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : `Failed to update ${category} settings`
      error.value = errorMessage
      console.error(`Error updating ${category} settings:`, err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Update general settings
   */
  async function updateGeneral(data: Partial<GeneralSettings>) {
    return updateCategorySettings('general', data as Record<string, unknown>)
  }

  /**
   * Update email settings
   */
  async function updateEmail(data: Partial<EmailSettings>) {
    return updateCategorySettings('email', data as Record<string, unknown>)
  }

  /**
   * Update member settings
   */
  async function updateMember(data: Partial<MemberSettings>) {
    return updateCategorySettings('member', data as Record<string, unknown>)
  }

  /**
   * Update service settings
   */
  async function updateService(data: Partial<ServiceSettings>) {
    return updateCategorySettings('service', data as Record<string, unknown>)
  }

  /**
   * Update order settings
   */
  async function updateOrder(data: Partial<OrderSettings>) {
    return updateCategorySettings('order', data as Record<string, unknown>)
  }

  /**
   * Clear error state
   */
  function clearError() {
    error.value = null
  }

  /**
   * Reset store to initial state
   */
  function $reset() {
    general.value = null
    email.value = null
    member.value = null
    service.value = null
    order.value = null
    permissions.value = null
    loading.value = false
    error.value = null
  }

  // ============================================================================
  // Return
  // ============================================================================

  return {
    // State
    general,
    email,
    member,
    service,
    order,
    permissions,
    loading,
    error,
    
    // Computed
    hasPermissions,
    canViewAnySettings,
    canChangeAnySettings,
    canViewCategory,
    canChangeCategory,
    availableTabs,
    equipmentManagerEmail,
    
    // Actions
    fetchPermissions,
    fetchAllSettings,
    fetchCategorySettings,
    updateCategorySettings,
    updateGeneral,
    updateEmail,
    updateMember,
    updateService,
    updateOrder,
    clearError,
    $reset
  }
})
