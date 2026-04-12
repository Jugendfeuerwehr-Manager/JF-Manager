/**
 * Settings API Client
 * HTTP client for settings management endpoints
 */

import apiClient from './index'
import type {
  AllSettings,
  GeneralSettings,
  EmailSettings,
  MemberSettings,
  ServiceSettings,
  OrderSettings,
  SettingsPermissions,
  SettingsCategory
} from '@/types/settings'

/**
 * Settings API endpoints
 */
export const settingsApi = {
  /**
   * Get all settings
   * GET /api/v1/settings/
   */
  getAll() {
    return apiClient.get<AllSettings>('/settings/')
  },

  /**
   * Get general settings
   * GET /api/v1/settings/general/
   */
  getGeneral() {
    return apiClient.get<GeneralSettings>('/settings/general/')
  },

  /**
   * Update general settings
   * PATCH /api/v1/settings/general/
   */
  updateGeneral(data: Partial<GeneralSettings>) {
    return apiClient.patch<GeneralSettings>('/settings/general/', data)
  },

  /**
   * Get email settings
   * GET /api/v1/settings/email/
   */
  getEmail() {
    return apiClient.get<EmailSettings>('/settings/email/')
  },

  /**
   * Update email settings
   * PATCH /api/v1/settings/email/
   */
  updateEmail(data: Partial<EmailSettings>) {
    return apiClient.patch<EmailSettings>('/settings/email/', data)
  },

  /**
   * Get member settings
   * GET /api/v1/settings/member/
   */
  getMember() {
    return apiClient.get<MemberSettings>('/settings/member/')
  },

  /**
   * Update member settings
   * PATCH /api/v1/settings/member/
   */
  updateMember(data: Partial<MemberSettings>) {
    return apiClient.patch<MemberSettings>('/settings/member/', data)
  },

  /**
   * Get service settings
   * GET /api/v1/settings/service/
   */
  getService() {
    return apiClient.get<ServiceSettings>('/settings/service/')
  },

  /**
   * Update service settings
   * PATCH /api/v1/settings/service/
   */
  updateService(data: Partial<ServiceSettings>) {
    return apiClient.patch<ServiceSettings>('/settings/service/', data)
  },

  /**
   * Get order settings
   * GET /api/v1/settings/order/
   */
  getOrder() {
    return apiClient.get<OrderSettings>('/settings/order/')
  },

  /**
   * Update order settings
   * PATCH /api/v1/settings/order/
   */
  updateOrder(data: Partial<OrderSettings>) {
    return apiClient.patch<OrderSettings>('/settings/order/', data)
  },

  /**
   * Get user permissions for settings
   * GET /api/v1/settings/permissions/
   */
  getPermissions() {
    return apiClient.get<SettingsPermissions>('/settings/permissions/')
  },

  /**
   * Get settings by category (helper method)
   */
  getByCategory(category: SettingsCategory) {
    switch (category) {
      case 'general':
        return this.getGeneral()
      case 'email':
      case 'email-templates':
        return this.getEmail()
      case 'member':
        return this.getMember()
      case 'service':
        return this.getService()
      case 'order':
        return this.getOrder()
      default:
        return this.getGeneral()
    }
  },

  /**
   * Update settings by category (helper method)
   */
  updateByCategory(category: SettingsCategory, data: Record<string, unknown>) {
    switch (category) {
      case 'general':
        return this.updateGeneral(data as Partial<GeneralSettings>)
      case 'email':
      case 'email-templates':
        return this.updateEmail(data as Partial<EmailSettings>)
      case 'member':
        return this.updateMember(data as Partial<MemberSettings>)
      case 'service':
        return this.updateService(data as Partial<ServiceSettings>)
      case 'order':
        return this.updateOrder(data as Partial<OrderSettings>)
      default:
        return this.updateGeneral(data as Partial<GeneralSettings>)
    }
  }
}

export default settingsApi
