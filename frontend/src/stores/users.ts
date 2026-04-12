/**
 * Users Pinia Store
 * 
 * Manages user state and authentication using Composition API pattern
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/types/api'
import { userApi } from '@/api/user'
import apiClient from '@/api/index'

export interface UsersListParams {
  limit?: number
  offset?: number
  search?: string
  is_active?: boolean
  is_staff?: boolean
}

export interface PaginatedUsersResponse {
  count: number
  next: string | null
  previous: string | null
  results: UserInfo[]
}

export const useUsersStore = defineStore('users', () => {
  // ============================================================================
  // State
  // ============================================================================

  // Current authenticated user
  const currentUser = ref<UserInfo | null>(null)
  const currentUserLoading = ref(false)
  const currentUserError = ref<string | null>(null)

  // Users list (for dropdowns, etc.)
  const users = ref<UserInfo[]>([])
  const usersLoading = ref(false)
  const usersError = ref<string | null>(null)
  const usersTotalCount = ref(0)

  // ============================================================================
  // Computed
  // ============================================================================

  const isAuthenticated = computed(() => currentUser.value !== null)
  const isStaff = computed(() => currentUser.value?.is_staff ?? false)
  const isSuperuser = computed(() => currentUser.value?.is_superuser ?? false)
  const activeUsers = computed(() => users.value.filter((u) => u.is_active))
  const staffUsers = computed(() => users.value.filter((u) => u.is_staff))

  // ============================================================================
  // Actions
  // ============================================================================

  /**
   * Fetch current authenticated user
   */
  async function fetchCurrentUser() {
    currentUserLoading.value = true
    currentUserError.value = null

    try {
      const response = await userApi.me()
      currentUser.value = response.data
      return currentUser.value
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch current user'
      currentUserError.value = message
      throw error
    } finally {
      currentUserLoading.value = false
    }
  }

  /**
   * Fetch list of users (for dropdowns, filters, etc.)
   */
  async function fetchUsers(params?: UsersListParams) {
    usersLoading.value = true
    usersError.value = null

    try {
      const response = await apiClient.get<PaginatedUsersResponse>('/users/', { params })
      
      // Extract results from paginated response
      users.value = response.data.results
      usersTotalCount.value = response.data.count
      
      return users.value
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch users'
      usersError.value = message
      throw error
    } finally {
      usersLoading.value = false
    }
  }

  /**
   * Get a single user by ID
   */
  async function fetchUser(userId: number) {
    try {
      const response = await apiClient.get<UserInfo>(`/users/${userId}/`)
      
      // Update in users list if exists
      const index = users.value.findIndex((u) => u.id === userId)
      if (index !== -1) {
        users.value[index] = response.data
      }
      
      return response.data
    } catch (error) {
      const message = error instanceof Error ? error.message : `Failed to fetch user ${userId}`
      throw new Error(message)
    }
  }

  /**
   * Update current user profile
   */
  async function updateProfile(data: Partial<UserInfo>) {
    currentUserLoading.value = true
    currentUserError.value = null

    try {
      const response = await userApi.updateProfile(data)
      currentUser.value = response.data
      return currentUser.value
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update profile'
      currentUserError.value = message
      throw error
    } finally {
      currentUserLoading.value = false
    }
  }

  /**
   * Clear all user data (e.g., on logout)
   */
  function clearUsers() {
    currentUser.value = null
    users.value = []
    usersTotalCount.value = 0
    currentUserError.value = null
    usersError.value = null
  }

  /**
   * Reset error states
   */
  function clearErrors() {
    currentUserError.value = null
    usersError.value = null
  }

  // ============================================================================
  // Return public API
  // ============================================================================

  return {
    // State
    currentUser,
    currentUserLoading,
    currentUserError,
    users,
    usersLoading,
    usersError,
    usersTotalCount,

    // Computed
    isAuthenticated,
    isStaff,
    isSuperuser,
    activeUsers,
    staffUsers,

    // Actions
    fetchCurrentUser,
    fetchUsers,
    fetchUser,
    updateProfile,
    clearUsers,
    clearErrors
  }
})
