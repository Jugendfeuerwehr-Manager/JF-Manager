import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth'
import { authApi } from '@/api/auth'
import { userApi } from '@/api/user'
import type { UserInfo } from '@/types/api'
import { hardNavigate } from '@/utils/navigation'
import router from '@/router'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'

const mockFetchDepartments = vi.fn().mockResolvedValue(undefined)
const mockInitializeActiveDepartment = vi.fn()
const mockClearDepartments = vi.fn()

// Mock API modules
vi.mock('@/api/auth')
vi.mock('@/api/user')
const mockRoute = vi.hoisted(() => ({ value: { path: '/' } }))
vi.mock('@/router', () => ({
  default: {
    push: vi.fn(),
    currentRoute: mockRoute,
  }
}))
vi.mock('@/utils/navigation', () => ({ hardNavigate: vi.fn() }))
vi.mock('@/stores/departments', () => ({
  useDepartmentsStore: () => ({
    fetchDepartments: mockFetchDepartments,
    initializeActiveDepartment: mockInitializeActiveDepartment,
    clearDepartments: mockClearDepartments,
    departments: [],
    activeDepartmentId: null,
  })
}))

// Helper to create mock Axios response
function createMockAxiosResponse<T>(data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: { headers: {} } as InternalAxiosRequestConfig
  }
}

// Helper to create complete mock user
function createMockUser(overrides: Partial<UserInfo> = {}): UserInfo {
  return {
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    first_name: 'Test',
    last_name: 'User',
    full_name: 'Test User',
    phone: '',
    mobile_phone: '',
    street: '',
    zip_code: '',
    city: '',
    is_staff: false,
    is_active: true,
    is_superuser: false,
    date_joined: '2026-01-01T00:00:00Z',
    last_login: '2026-04-12T00:00:00Z',
    avatar: null,
    avatar_url: null,
    dsgvo_internal: true,
    dsgvo_external: false,
    groups: [],
    permissions: [],
    department_roles: [],
    has_org_wide_access: false,
    favorite_department: null,
    auth_source: 'local',
    ...overrides
  } as UserInfo
}

describe('Auth Store', () => {
  beforeEach(() => {
    // Create a fresh pinia instance for each test
    setActivePinia(createPinia())
    
    // Clear localStorage
    localStorage.clear()
    
    // Reset all mocks
    vi.clearAllMocks()
    mockFetchDepartments.mockResolvedValue(undefined)
  })

  describe('State', () => {
    it('keeps auth group permissions distinct from member group permissions', () => {
      const store = useAuthStore()
      store.user = createMockUser({ permissions: ['view_group'], qualified_permissions: ['auth.view_group'] })
      expect(store.hasPerm('auth.view_group')).toBe(true)
      expect(store.canAccessModule('members.view_group')).toBe(false)
    })
    it('includes department subject roles alongside global administration without merging their namespaces', () => {
      const store = useAuthStore()
      store.user = createMockUser({ has_org_wide_access: true, permissions: ['view_group'], qualified_permissions: ['auth.view_group'], department_roles: [{ department_id: 1, permissions: ['view_member'], qualified_permissions: ['members.view_member'], groups: [], department_name: 'Test', department_code: 'test', department_color: '#000000' }] })
      expect(store.hasPerm('members.view_member')).toBe(true)
      expect(store.hasPerm('members.view_group')).toBe(false)
    })
    it('starts signed out without reading tokens from storage', () => {
      localStorage.setItem('accessToken', 'legacy-access')
      const store = useAuthStore()

      expect(store.session).toBeNull()
      expect(store.user).toBeNull()
      expect(store.isAuthenticated).toBe(false)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('initialize removes legacy JWT storage and loads the session once', async () => {
      localStorage.setItem('accessToken', 'legacy-access')
      localStorage.setItem('refreshToken', 'legacy-refresh')
      vi.mocked(authApi.session).mockResolvedValue(createMockAxiosResponse({ authenticated: true }))
      vi.mocked(userApi.me).mockResolvedValue(createMockAxiosResponse(createMockUser()))
      const store = useAuthStore()

      await Promise.all([store.initialize(), store.initialize()])

      expect(localStorage.getItem('accessToken')).toBeNull()
      expect(localStorage.getItem('refreshToken')).toBeNull()
      expect(authApi.session).toHaveBeenCalledTimes(1)
      expect(store.isAuthenticated).toBe(true)
    })

    it('initialize treats an unreachable session endpoint as signed out', async () => {
      vi.mocked(authApi.session).mockRejectedValue(new Error('offline'))
      const store = useAuthStore()
      await store.initialize()
      expect(store.isAuthenticated).toBe(false)
    })
  })

  describe('Computed', () => {
    it('isAuthenticated needs an authenticated session and a loaded user', () => {
      const store = useAuthStore()
      store.session = { authenticated: true }
      expect(store.isAuthenticated).toBe(false)
      store.user = createMockUser()
      expect(store.isAuthenticated).toBe(true)
      store.session = { authenticated: false }
      expect(store.isAuthenticated).toBe(false)
    })

    it('reports a pending second factor and mandatory setup', () => {
      const store = useAuthStore()
      store.session = { authenticated: false, mfa_required: true }
      expect(store.mfaPending).toBe(true)
      store.session = { authenticated: true, mfa_setup_required: true }
      expect(store.mfaPending).toBe(false)
      expect(store.mfaSetupRequired).toBe(true)
    })

    it('userFullName returns user full name', () => {
      const store = useAuthStore()
      store.user = createMockUser({ full_name: 'Test User' })
      
      expect(store.userFullName).toBe('Test User')
    })

    it('userFullName returns empty string when no user', () => {
      const store = useAuthStore()
      
      expect(store.userFullName).toBe('')
    })

    it('permissions returns user permissions', () => {
      const store = useAuthStore()
      store.user = createMockUser({ permissions: ['view_members', 'edit_orders'] })
      
      expect(store.permissions).toEqual(['view_members', 'edit_orders'])
    })

    it('hasPermission returns true for superuser', () => {
      const store = useAuthStore()
      store.user = createMockUser({ is_staff: true, is_superuser: true })
      
      expect(store.hasPermission('any_permission')).toBe(true)
    })

    it('hasPermission returns true when user has permission', () => {
      const store = useAuthStore()
      store.user = createMockUser({ permissions: ['view_members'] })
      
      expect(store.hasPermission('view_members')).toBe(true)
    })

    it('hasPermission returns false when user lacks permission', () => {
      const store = useAuthStore()
      store.user = createMockUser({ permissions: ['view_members'] })
      
      expect(store.hasPermission('edit_orders')).toBe(false)
    })
  })

  describe('Actions', () => {
    describe('login', () => {
      it('signs in with a session cookie and never stores tokens', async () => {
        const mockUserResponse = createMockAxiosResponse(createMockUser())
        vi.mocked(authApi.login).mockResolvedValue(createMockAxiosResponse({ authenticated: true }))
        vi.mocked(userApi.me).mockResolvedValue(mockUserResponse)

        const store = useAuthStore()
        const result = await store.login('testuser', 'password')

        expect(result).toEqual({ authenticated: true })
        expect(store.isAuthenticated).toBe(true)
        expect(store.user).toEqual(mockUserResponse.data)
        expect(localStorage.length).toBe(0)
        expect(mockFetchDepartments).toHaveBeenCalledTimes(1)
        expect(mockInitializeActiveDepartment).toHaveBeenCalledWith(mockUserResponse.data)
      })

      it('stops after the password when a second factor is required', async () => {
        vi.mocked(authApi.login).mockResolvedValue(createMockAxiosResponse({ authenticated: false, mfa_required: true }))
        const store = useAuthStore()

        const result = await store.login('testuser', 'password')

        expect(result.mfa_required).toBe(true)
        expect(store.mfaPending).toBe(true)
        expect(store.isAuthenticated).toBe(false)
        expect(userApi.me).not.toHaveBeenCalled()
      })

      it('completes the login with a verified code', async () => {
        vi.mocked(authApi.verifyMfa).mockResolvedValue(createMockAxiosResponse({ authenticated: true }))
        vi.mocked(userApi.me).mockResolvedValue(createMockAxiosResponse(createMockUser()))
        const store = useAuthStore()
        store.session = { authenticated: false, mfa_required: true }

        await store.verifyMfa('123456')

        expect(authApi.verifyMfa).toHaveBeenCalledWith('123456')
        expect(store.isAuthenticated).toBe(true)
      })

      it('handles login failure', async () => {
        vi.mocked(authApi.login).mockRejectedValue(new Error('Invalid credentials'))
        
        const store = useAuthStore()
        
        await expect(store.login('testuser', 'wrong-password')).rejects.toThrow()
        expect(store.error).toBeTruthy()
        expect(store.isAuthenticated).toBe(false)
      })

      it('sets loading state during login', async () => {
        let loadingDuringLogin = false
        
        vi.mocked(authApi.login).mockImplementation(async () => {
          const store = useAuthStore()
          loadingDuringLogin = store.loading
          return createMockAxiosResponse({ authenticated: true })
        })
        
        vi.mocked(userApi.me).mockResolvedValue(
          createMockAxiosResponse(createMockUser())
        )
        
        const store = useAuthStore()
        await store.login('testuser', 'password')
        
        expect(loadingDuringLogin).toBe(true)
        expect(store.loading).toBe(false)
      })
    })

    describe('logout', () => {
      it('ends the server session, clears state and reloads the login page', async () => {
        vi.mocked(authApi.logout).mockResolvedValue(createMockAxiosResponse({ authenticated: false }))
        const store = useAuthStore()
        store.session = { authenticated: true }
        store.user = createMockUser()

        await store.logout()

        expect(authApi.logout).toHaveBeenCalled()
        expect(store.user).toBeNull()
        expect(store.session).toBeNull()
        expect(mockClearDepartments).toHaveBeenCalled()
        expect(hardNavigate).toHaveBeenCalledWith('/login')
      })

      it('clears local state even when the server is unreachable', async () => {
        vi.mocked(authApi.logout).mockRejectedValue(new Error('offline'))
        const store = useAuthStore()
        store.session = { authenticated: true }
        store.user = createMockUser()

        await store.logout()

        expect(store.user).toBeNull()
        expect(hardNavigate).toHaveBeenCalledWith('/login')
      })
    })

    describe('session expiry', () => {
      it('redirects to login once the server session has ended', () => {
        const store = useAuthStore()
        store.session = { authenticated: true }
        store.user = createMockUser()

        store.handleSessionExpired()
        store.handleSessionExpired()

        expect(store.user).toBeNull()
        expect(hardNavigate).toHaveBeenCalledTimes(1)
        expect(hardNavigate).toHaveBeenCalledWith('/login?expired=1')
      })
    })

    describe('mandatory MFA setup', () => {
      async function signedInStore() {
        vi.mocked(authApi.session).mockResolvedValue(createMockAxiosResponse({ authenticated: true }))
        vi.mocked(userApi.me).mockResolvedValue(createMockAxiosResponse(createMockUser({ is_staff: true })))
        const store = useAuthStore()
        await store.initialize()
        return store
      }

      async function failWithSetupRequired(times: number) {
        const { default: client } = await import('@/api')
        const { AxiosError, AxiosHeaders } = await import('axios')
        client.defaults.adapter = async config => {
          throw new AxiosError('forbidden', 'ERR_BAD_REQUEST', config, undefined, {
            status: 403, statusText: 'Forbidden', data: { code: 'mfa_setup_required' }, headers: new AxiosHeaders(), config,
          })
        }
        for (let index = 0; index < times; index += 1) await client.get('/members/').catch(() => undefined)
      }

      it('redirects to the setup only once for many rejected requests', async () => {
        mockRoute.value = { path: '/members' }
        const store = await signedInStore()
        await failWithSetupRequired(5)
        expect(store.mfaSetupRequired).toBe(true)
        expect(router.push).toHaveBeenCalledTimes(1)
      })

      it('does not redirect again from the setup page', async () => {
        mockRoute.value = { path: '/profile' }
        await signedInStore()
        await failWithSetupRequired(3)
        expect(router.push).not.toHaveBeenCalled()
      })
    })
  })
})
