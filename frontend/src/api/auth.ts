import apiClient from './index'
import type { LoginRequest, LoginResponse, TokenRefreshResponse } from '@/types/api'

export interface PasswordResetRequest {
  email: string
}

export interface PasswordResetConfirm {
  token: string
  uid: string
  new_password: string
  new_password_confirm: string
}

export interface PasswordChange {
  old_password: string
  new_password: string
  new_password_confirm: string
}

export interface MessageResponse {
  message: string
}

export const authApi = {
  async login(credentials: LoginRequest) {
    return apiClient.post<LoginResponse>('/auth/login/', credentials)
  },

  async refresh(refreshToken: string) {
    return apiClient.post<TokenRefreshResponse>('/auth/refresh/', { refresh: refreshToken })
  },

  async verify(token: string) {
    return apiClient.post('/auth/verify/', { token })
  },

  logout() {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
  },

  async requestPasswordReset(email: string) {
    return apiClient.post<MessageResponse>('/users/request_password_reset/', { email })
  },

  async resetPassword(data: PasswordResetConfirm) {
    return apiClient.post<MessageResponse>('/users/reset_password/', data)
  },

  async changePassword(data: PasswordChange) {
    return apiClient.post<MessageResponse>('/users/change_password/', data)
  }
}
