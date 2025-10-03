import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import { userApi } from '@/api/user'
import type { UserInfo } from '@/types/api'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  // State
  const accessToken = ref<string | null>(localStorage.getItem('accessToken'))
  const refreshToken = ref<string | null>(localStorage.getItem('refreshToken'))
  const user = ref<UserInfo | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value)
  const userFullName = computed(() => user.value?.full_name || '')
  const permissions = computed(() => user.value?.permissions || [])
  const hasPermission = (permission: string) => {
    return user.value?.is_superuser || permissions.value.includes(permission)
  }

  // Actions
  async function login(username: string, password: string) {
    loading.value = true
    error.value = null

    try {
      const response = await authApi.login({ username, password })

      accessToken.value = response.data.access
      refreshToken.value = response.data.refresh

      // Store tokens in localStorage
      localStorage.setItem('accessToken', response.data.access)
      localStorage.setItem('refreshToken', response.data.refresh)

      // Fetch user data
      await fetchUser()

      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    try {
      const response = await userApi.me()
      user.value = response.data
    } catch (err: any) {
      error.value = 'Failed to fetch user data'
      throw err
    }
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) {
      throw new Error('No refresh token available')
    }

    try {
      const response = await authApi.refresh(refreshToken.value)
      accessToken.value = response.data.access
      localStorage.setItem('accessToken', response.data.access)
      if (response.data.refresh) {
        refreshToken.value = response.data.refresh
        localStorage.setItem('refreshToken', response.data.refresh)
      }
    } catch (err) {
      // Refresh failed, logout
      logout()
      throw err
    }
  }

  async function updateProfile(data: Partial<UserInfo>) {
    try {
      const response = await userApi.updateProfile(data)
      user.value = response.data
      return response.data
    } catch (err: any) {
      error.value = 'Failed to update profile'
      throw err
    }
  }

  function logout() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null

    authApi.logout()
    router.push('/login')
  }

  // Initialize - Check if tokens exist and fetch user
  async function initialize() {
    if (accessToken.value) {
      try {
        await fetchUser()
      } catch (err) {
        // Token invalid, logout
        logout()
      }
    }
  }

  return {
    // State
    accessToken,
    refreshToken,
    user,
    loading,
    error,
    // Getters
    isAuthenticated,
    userFullName,
    permissions,
    hasPermission,
    // Actions
    login,
    fetchUser,
    refreshAccessToken,
    updateProfile,
    logout,
    initialize
  }
})
