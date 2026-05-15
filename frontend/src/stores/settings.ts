/**
 * Settings Store
 * Pinia store for managing application settings
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { settingsApi } from '@/api/settings'
import { oidcApi } from '@/api/oidc'
import type {
  GeneralSettings,
  EmailSettings,
  MemberSettings,
  ServiceSettings,
  OrderSettings,
  LdapSettings,
  LdapBrowseRequest,
  LdapBrowseResult,
  LdapDepartmentRoleMapping,
  LdapDepartmentRoleMappingCreate,
  SettingsPermissions,
  SettingsCategory
} from '@/types/settings'
import type { OIDCSettings } from '@/types/oidc'

export const useSettingsStore = defineStore('settings', () => {
  // ============================================================================
  // State
  // ============================================================================

  const general = ref<GeneralSettings | null>(null)
  const email = ref<EmailSettings | null>(null)
  const member = ref<MemberSettings | null>(null)
  const service = ref<ServiceSettings | null>(null)
  const order = ref<OrderSettings | null>(null)
  const ldap = ref<LdapSettings | null>(null)
  const oidc = ref<OIDCSettings | null>(null)
  const permissions = ref<SettingsPermissions | null>(null)
  const departmentMappings = ref<LdapDepartmentRoleMapping[]>([])
  
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

    if (canViewCategory.value('ldap')) {
      tabs.push({
        id: 'ldap',
        title: 'LDAP',
        icon: 'pi pi-shield',
        description: 'LDAP Anmeldung und Gruppen-Synchronisation'
      })
    }

    if (canViewCategory.value('oidc')) {
      tabs.push({
        id: 'oidc',
        title: 'OIDC / SSO',
        icon: 'pi pi-sign-in',
        description: 'Single Sign-On via OpenID Connect'
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

  const navGroups = computed(() => {
    const tabMap = new Map(availableTabs.value.map((t) => [t.id, t]))

    const groupDefs: Array<{ label: string; icon: string; ids: SettingsCategory[] }> = [
      { label: 'Organisation', icon: 'pi pi-building', ids: ['general'] },
      { label: 'Kommunikation', icon: 'pi pi-envelope', ids: ['email', 'email-templates'] },
      { label: 'Mitglieder', icon: 'pi pi-users', ids: ['member'] },
      { label: 'Betrieb', icon: 'pi pi-briefcase', ids: ['service', 'order'] },
      { label: 'Sicherheit', icon: 'pi pi-shield', ids: ['ldap', 'oidc'] },
    ]

    return groupDefs
      .map((g) => ({
        label: g.label,
        icon: g.icon,
        items: g.ids.flatMap((id) => (tabMap.has(id) ? [tabMap.get(id)!] : [])),
      }))
      .filter((g) => g.items.length > 0)
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
      if (data.ldap) ldap.value = data.ldap
      if (data.oidc) oidc.value = data.oidc as unknown as OIDCSettings
      
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
        case 'ldap':
          ldap.value = response.data as LdapSettings
          break
        case 'oidc': {
          const resp = await oidcApi.getSettings()
          oidc.value = resp.data
          return resp.data
        }
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
        case 'ldap':
          ldap.value = response.data as LdapSettings
          break
        case 'oidc': {
          const resp = await oidcApi.updateSettings(data as Partial<OIDCSettings>)
          oidc.value = resp.data
          return resp.data
        }
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
   * Update LDAP settings
   */
  async function updateLdap(data: Partial<LdapSettings>) {
    return updateCategorySettings('ldap', data as Record<string, unknown>)
  }

  async function updateOidc(data: Partial<OIDCSettings>) {
    return updateCategorySettings('oidc', data as Record<string, unknown>)
  }

  /**
   * Test LDAP connection
   */
  async function testLdapConnection() {
    try {
      loading.value = true
      error.value = null
      const response = await settingsApi.testLdapConnection()
      return response.data
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to test LDAP connection'
      error.value = errorMessage
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Browse LDAP directory at a given DN
   */
  async function browseLdapDn(params: LdapBrowseRequest): Promise<LdapBrowseResult> {
    const response = await settingsApi.browseLdap(params)
    return response.data
  }

  /**
   * Fetch LDAP → Department role mappings
   */
  async function fetchDepartmentMappings() {
    try {
      const response = await settingsApi.listDepartmentMappings()
      departmentMappings.value = response.data
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch department mappings'
      error.value = errorMessage
      throw err
    }
  }

  /**
   * Create a new LDAP → Department role mapping
   */
  async function createDepartmentMapping(data: LdapDepartmentRoleMappingCreate) {
    const response = await settingsApi.createDepartmentMapping(data)
    departmentMappings.value.push(response.data)
    return response.data
  }

  /**
   * Delete a LDAP → Department role mapping
   */
  async function deleteDepartmentMapping(id: number) {
    await settingsApi.deleteDepartmentMapping(id)
    departmentMappings.value = departmentMappings.value.filter((m) => m.id !== id)
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
    ldap.value = null
    oidc.value = null
    permissions.value = null
    departmentMappings.value = []
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
    ldap,
    oidc,
    permissions,
    departmentMappings,
    loading,
    error,
    
    // Computed
    hasPermissions,
    canViewAnySettings,
    canChangeAnySettings,
    canViewCategory,
    canChangeCategory,
    availableTabs,
    navGroups,
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
    updateLdap,
    updateOidc,
    testLdapConnection,
    browseLdapDn,
    fetchDepartmentMappings,
    createDepartmentMapping,
    deleteDepartmentMapping,
    clearError,
    $reset
  }
})
