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
   * Update current user profile
   */
  async updateProfile(data: Partial<UserInfo>) {
    const user = await this.me()
    return apiClient.patch<UserInfo>(`/users/${user.data.id}/`, data)
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
