import apiClient from './index'
import type { UserInfo, AppSettings } from '@/types/api'

export const userApi = {
  /**
   * Get current authenticated user information
   */
  async me() {
    return apiClient.get<UserInfo>('/users/me/')
  },

  /**
   * Update current user profile (also the only profile route open to portal accounts)
   */
  async updateProfile(data: Partial<UserInfo>) {
    return apiClient.patch<UserInfo>('/users/me/', data)
  }
}

export const settingsApi = {
  /**
   * Get application settings
   */
  async get() {
    return apiClient.get<AppSettings>('/settings/')
  }
}
