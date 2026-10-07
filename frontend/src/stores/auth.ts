import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type SessionStatus } from '@/api/auth'
import { onSessionProblem } from '@/api'
import { userApi } from '@/api/user'
import type { UserInfo } from '@/types/api'
import router from '@/router'
import { getApiErrorMessage } from '@/utils/apiError'
import { getPasskeyAssertion, passkeyErrorMessage } from '@/utils/webauthn'
import { hardNavigate } from '@/utils/navigation'
import { useDepartmentsStore } from '@/stores/departments'

// Credentials from the former JWT login; removed on every start.
const LEGACY_STORAGE_KEYS = ['accessToken', 'refreshToken']
// Only the most recently initialised store reacts to session problems (HMR, tests).
let unsubscribeSessionProblems: (() => void) | null = null

export const useAuthStore = defineStore('auth', () => {
  // State
  const session = ref<SessionStatus | null>(null)
  const user = ref<UserInfo | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let initializing: Promise<void> | null = null

  // Getters
  const isAuthenticated = computed(() => !!session.value?.authenticated && !!user.value)
  const mfaPending = computed(() => !!session.value?.mfa_required && !session.value.authenticated)
  const mfaMethods = computed(() => session.value?.mfa_methods ?? { totp: true, passkey: false })
  const mfaSetupRequired = computed(() => !!session.value?.authenticated && !!session.value.mfa_setup_required)
  const userFullName = computed(() => user.value?.full_name || '')

  // Global rights remain global; department rights follow the selected area.
  // Organisation visibility never turns a scoped right into a global right.
  const contextualRoles = computed(() => {
    const id = useDepartmentsStore().activeDepartmentId
    return user.value?.department_roles.filter(role => id === null || role.department_id === id) ?? []
  })
  const permissions = computed((): string[] => [...new Set([
    ...(user.value?.permissions ?? []), ...contextualRoles.value.flatMap(role => role.permissions),
  ])])
  const qualifiedPermissions = computed((): string[] => [...new Set([
    ...(user.value?.qualified_permissions ?? []), ...contextualRoles.value.flatMap(role => role.qualified_permissions ?? []),
  ])])

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
   * Legacy profiles without qualified names retain compatibility.
   */
  const hasPerm = (appPerm: string): boolean => {
    if (!user.value) return false
    if (user.value.is_superuser || permissions.value.includes('superuser')) return true
    const codename = appPerm.includes('.') ? (appPerm.split('.')[1] ?? appPerm) : appPerm
    if (appPerm.includes('.') && user.value.qualified_permissions !== undefined) return qualifiedPermissions.value.includes(appPerm)
    return permissions.value.includes(appPerm) || permissions.value.includes(codename)
  }

  /**
   * Returns true if the user can access the given module.
   * Requires the explicit subject permission in the selected context.
   */
  const canAccessModule = (viewPerm: string): boolean => {
    return hasPerm(viewPerm)
  }

  // Actions
  async function applySession(status: SessionStatus) {
    session.value = status
    if (status.authenticated) {
      if (!user.value) await fetchUser()
    } else {
      user.value = null
    }
    return status
  }

  /** Password step; resolves with `mfa_required` when a code must follow. */
  async function login(username: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const response = await authApi.login({ username, password })
      return await applySession(response.data)
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Anmeldung fehlgeschlagen.')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function verifyMfa(code: string) {
    loading.value = true
    error.value = null
    try {
      const response = await authApi.verifyMfa(code)
      return await applySession(response.data)
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Der Code ist ungültig.')
      throw err
    } finally {
      loading.value = false
    }
  }

  /** Finishes the pending login with a passkey (SEC-11). */
  async function verifyMfaPasskey() {
    loading.value = true
    error.value = null
    try {
      const options = (await authApi.loginPasskeyOptions()).data
      const assertion = await getPasskeyAssertion(options)
      const response = await authApi.verifyMfaPasskey(assertion)
      return await applySession(response.data)
    } catch (err) {
      error.value = passkeyErrorMessage(err) ?? getApiErrorMessage(err, 'Der Passkey konnte nicht bestätigt werden.')
      throw err
    } finally {
      loading.value = false
    }
  }

  /** Reads the session state without counting as user activity. */
  async function refreshSession() {
    const response = await authApi.session()
    return applySession(response.data)
  }

  async function fetchUser() {
    try {
      const response = await userApi.me()
      user.value = response.data
      // Load departments and set the default active department
      const departmentsStore = useDepartmentsStore()
      await departmentsStore.fetchDepartments()
      departmentsStore.initializeActiveDepartment(response.data)

      // Warm up members/servicebook/parents caches in the background for the
      // active department (realm) so those modules feel instant. Never block
      // on this — it's a fire-and-forget cache prime.
      import('@/composables/useWarmup').then(({ useWarmup }) => {
        const { warmupStores, watchDepartmentChanges } = useWarmup()
        warmupStores()
        watchDepartmentChanges()
      })
    } catch (err) {
      error.value = 'Failed to fetch user data'
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

  function clearLocalState() {
    session.value = null
    user.value = null
    useDepartmentsStore().clearDepartments()
    sessionStorage.removeItem('oidc_return_url')
  }

  /** Ends the server session, then reloads so no store keeps previous data. */
  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // The local state is discarded regardless; the session expires server-side.
    }
    clearLocalState()
    hardNavigate('/login')
  }

  function handleSessionExpired() {
    if (!session.value?.authenticated) return
    clearLocalState()
    hardNavigate('/login?expired=1')
  }

  /**
   * Initiate an OIDC login by redirecting the browser to the IdP. The backend
   * keeps state, nonce, PKCE verifier and return path in the session.
   */
  async function loginWithOidc(next?: string) {
    const { oidcApi } = await import('@/api/oidc')
    const targetNext = next || router.currentRoute.value.fullPath || '/'
    const response = await oidcApi.getLoginUrl(targetNext)
    window.location.href = response.data.authorization_url
  }

  /** Loads session and user once; the router guard awaits this before deciding. */
  function initialize() {
    if (!initializing) {
      LEGACY_STORAGE_KEYS.forEach(key => localStorage.removeItem(key))
      unsubscribeSessionProblems?.()
      unsubscribeSessionProblems = onSessionProblem(problem => {
        if (problem === 'expired') handleSessionExpired()
        else if (session.value) {
          // Several requests may report this at once; redirect only once and
          // never from the setup page itself (that would loop via the guard).
          const alreadyKnown = session.value.mfa_setup_required
          session.value = { ...session.value, mfa_setup_required: true }
          if (!alreadyKnown && router.currentRoute.value.path !== '/profile') {
            void router.push({ path: '/profile', query: { mfa: 'setup' } })
          }
        }
      })
      initializing = refreshSession().then(() => undefined).catch(() => {
        session.value = { authenticated: false }
      })
    }
    return initializing
  }

  return {
    // State
    session,
    user,
    loading,
    error,
    // Getters
    isAuthenticated,
    mfaPending,
    mfaMethods,
    mfaSetupRequired,
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
    verifyMfa,
    verifyMfaPasskey,
    refreshSession,
    fetchUser,
    updateProfile,
    logout,
    handleSessionExpired,
    initialize,
    loginWithOidc,
  }
})
