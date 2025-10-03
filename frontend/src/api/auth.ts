import apiClient from './index'
import type { LoginRequest, LoginResponse, TokenRefreshRequest, TokenRefreshResponse } from '@/types/api'

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
  }
}
