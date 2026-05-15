import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import { userApi } from '@/api/user'
import type { UserInfo } from '@/types/api'
import router from '@/router'
import { getApiErrorMessage } from '@/utils/apiError'
import { useDepartmentsStore } from '@/stores/departments'

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

  /**
   * Effective permissions for the currently active department context.
   * - If the user is org-wide (staff/superuser) or "All Departments" is active,
   *   returns the full union of permissions from the server.
   * - If a specific department is active, returns only the permissions the user
   *   has through their groups in that department.
   */
  const permissions = computed((): string[] => {
    if (!user.value) return []
    // org-wide users always get all their permissions regardless of active dept
    if (user.value.has_org_wide_access || user.value.is_superuser) {
      return user.value.permissions
    }
    const deptStore = useDepartmentsStore()
    const activeDeptId = deptStore.activeDepartmentId
    if (activeDeptId === null) {
      // No specific dept selected → union of all dept permissions
      return user.value.permissions
    }
    // A concrete department narrows the effective permission set to the role
    // groups assigned for that department only. UI guards and button states
    // intentionally follow this context-sensitive permission view.
    const role = user.value.department_roles.find((r) => r.department_id === activeDeptId)
    return role?.permissions ?? []
  })

  /** True for staff / superuser / users with can_access_all_departments permission */
  const isOrgWide = computed(() => user.value?.has_org_wide_access ?? false)

  /** True for users that are staff or superuser (full admin access) */
  const isStaff = computed(() => (user.value?.is_staff || user.value?.is_superuser) ?? false)

  /** True when the user is assigned to at least one department */
  const hasDeptRole = computed(() => (user.value?.department_roles?.length ?? 0) > 0)

  /**
   * Check a single Django permission codename (without app_label prefix).
   * Superusers always pass. Regular users must have the permission in their set.
   * Example: hasPermission('view_member'), hasPermission('add_order')
   */
  const hasPermission = (permission: string) => {
    if (!user.value) return false
    if (user.value.is_superuser || permissions.value.includes('superuser')) return true
    return permissions.value.includes(permission)
  }

  /**
   * Check app-label-qualified permission, e.g. 'members.view_member'.
   * Also strips the app label and checks the bare codename.
   */
  const hasPerm = (appPerm: string): boolean => {
    if (!user.value) return false
    if (user.value.is_superuser || permissions.value.includes('superuser')) return true
    const codename = appPerm.includes('.') ? (appPerm.split('.')[1] ?? appPerm) : appPerm
    return permissions.value.includes(appPerm) || permissions.value.includes(codename)
  }

  /**
   * Returns true if the user can access the given module.
   * Staff/org-wide users can access everything.
   * Other users need at least view permission for the relevant model.
   */
  const canAccessModule = (viewPerm: string): boolean => {
    if (isOrgWide.value) return true
    return hasPerm(viewPerm)
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
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Login failed')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    try {
      const response = await userApi.me()
      user.value = response.data
      // Load departments and set the default active department
      const departmentsStore = useDepartmentsStore()
      await departmentsStore.fetchDepartments()
      departmentsStore.initializeActiveDepartment(response.data)
    } catch (err) {
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
    } catch (err) {
      error.value = 'Failed to update profile'
      throw err
    }
  }

  function logout() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null

    const departmentsStore = useDepartmentsStore()
    departmentsStore.clearDepartments()

    authApi.logout()
    router.push('/login')
  }

  /**
   * Initiate an OIDC login by redirecting the browser to the IdP.
   * Saves the intended destination URL in sessionStorage so the callback
   * view can restore it after a successful login.
   */
  async function loginWithOidc(next?: string) {
    const { oidcApi } = await import('@/api/oidc')
    const targetNext = next || router.currentRoute.value.fullPath || '/'
    sessionStorage.setItem('oidc_return_url', targetNext)
    const response = await oidcApi.getLoginUrl(targetNext)
    window.location.href = response.data.authorization_url
  }

  /**
   * Store OIDC-issued JWT tokens (called from OIDCCallbackView after exchange).
   * Triggers the same user-fetch flow as a normal login.
   */
  async function setOIDCTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('accessToken', access)
    localStorage.setItem('refreshToken', refresh)
    await fetchUser()
  }

  // Initialize - Check if tokens exist and fetch user
  async function initialize() {
    if (accessToken.value) {
      try {
        await fetchUser()
      } catch {
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
    isOrgWide,
    isStaff,
    hasDeptRole,
    hasPermission,
    hasPerm,
    canAccessModule,
    // Actions
    login,
    fetchUser,
    refreshAccessToken,
    updateProfile,
    logout,
    initialize,
    loginWithOidc,
    setOIDCTokens,
  }
})
