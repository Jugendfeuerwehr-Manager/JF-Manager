import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth'
import { authApi } from '@/api/auth'
import { userApi } from '@/api/user'
import type { UserInfo } from '@/types/api'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'

// Mock API modules
vi.mock('@/api/auth')
vi.mock('@/api/user')
vi.mock('@/router', () => ({
  default: {
    push: vi.fn()
  }
}))
vi.mock('@/stores/departments', () => ({
  useDepartmentsStore: () => ({
    fetchDepartments: vi.fn().mockResolvedValue(undefined),
    clearDepartments: vi.fn(),
    departments: [],
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
    ...overrides
  }
}

describe('Auth Store', () => {
  beforeEach(() => {
    // Create a fresh pinia instance for each test
    setActivePinia(createPinia())
    
    // Clear localStorage
    localStorage.clear()
    
    // Reset all mocks
    vi.clearAllMocks()
  })

  describe('State', () => {
    it('initializes with null tokens when no localStorage data', () => {
      const store = useAuthStore()
      
      expect(store.accessToken).toBeNull()
      expect(store.refreshToken).toBeNull()
      expect(store.user).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('initializes with tokens from localStorage', () => {
      localStorage.setItem('accessToken', 'test-access-token')
      localStorage.setItem('refreshToken', 'test-refresh-token')
      
      const store = useAuthStore()
      
      expect(store.accessToken).toBe('test-access-token')
      expect(store.refreshToken).toBe('test-refresh-token')
    })
  })

  describe('Computed', () => {
    it('isAuthenticated returns true when access token exists', () => {
      const store = useAuthStore()
      store.accessToken = 'test-token'
      
      expect(store.isAuthenticated).toBe(true)
    })

    it('isAuthenticated returns false when no access token', () => {
      const store = useAuthStore()
      store.accessToken = null
      
      expect(store.isAuthenticated).toBe(false)
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
      it('successfully logs in and stores tokens', async () => {
        const mockAuthResponse = createMockAxiosResponse({
          access: 'new-access-token',
          refresh: 'new-refresh-token'
        })
        
        const mockUserResponse = createMockAxiosResponse(createMockUser())
        
        vi.mocked(authApi.login).mockResolvedValue(mockAuthResponse)
        vi.mocked(userApi.me).mockResolvedValue(mockUserResponse)
        
        const store = useAuthStore()
        const result = await store.login('testuser', 'password')
        
        expect(result).toBe(true)
        expect(store.accessToken).toBe('new-access-token')
        expect(store.refreshToken).toBe('new-refresh-token')
        expect(store.user).toEqual(mockUserResponse.data)
        expect(localStorage.getItem('accessToken')).toBe('new-access-token')
        expect(localStorage.getItem('refreshToken')).toBe('new-refresh-token')
      })

      it('handles login failure', async () => {
        vi.mocked(authApi.login).mockRejectedValue(new Error('Invalid credentials'))
        
        const store = useAuthStore()
        
        await expect(store.login('testuser', 'wrong-password')).rejects.toThrow()
        expect(store.error).toBeTruthy()
        expect(store.accessToken).toBeNull()
      })

      it('sets loading state during login', async () => {
        let loadingDuringLogin = false
        
        vi.mocked(authApi.login).mockImplementation(async () => {
          const store = useAuthStore()
          loadingDuringLogin = store.loading
          return createMockAxiosResponse({
            access: 'token',
            refresh: 'refresh'
          })
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
      it('clears tokens and user data', () => {
        const store = useAuthStore()
        store.accessToken = 'test-token'
        store.refreshToken = 'test-refresh'
        store.user = createMockUser()
        
        store.logout()
        
        expect(store.accessToken).toBeNull()
        expect(store.refreshToken).toBeNull()
        expect(store.user).toBeNull()
      })

      it('calls authApi.logout', () => {
        const store = useAuthStore()
        store.logout()
        
        expect(authApi.logout).toHaveBeenCalled()
      })
    })

    describe('refreshAccessToken', () => {
      it('refreshes access token successfully', async () => {
        const store = useAuthStore()
        store.refreshToken = 'old-refresh-token'
        
        vi.mocked(authApi.refresh).mockResolvedValue(
          createMockAxiosResponse({ access: 'new-access-token' })
        )
        
        await store.refreshAccessToken()
        
        expect(store.accessToken).toBe('new-access-token')
        expect(localStorage.getItem('accessToken')).toBe('new-access-token')
      })

      it('throws error when no refresh token', async () => {
        const store = useAuthStore()
        store.refreshToken = null
        
        await expect(store.refreshAccessToken()).rejects.toThrow('No refresh token available')
      })

      it('logs out on refresh failure', async () => {
        const store = useAuthStore()
        store.refreshToken = 'invalid-token'
        store.accessToken = 'old-token'
        
        vi.mocked(authApi.refresh).mockRejectedValue(new Error('Invalid refresh token'))
        
        await expect(store.refreshAccessToken()).rejects.toThrow()
        
        expect(store.accessToken).toBeNull()
        expect(store.refreshToken).toBeNull()
      })
    })
  })
})
