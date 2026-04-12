import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../auth'
import { authApi } from '@/api/auth'
import { userApi } from '@/api/user'

// Mock API modules
vi.mock('@/api/auth')
vi.mock('@/api/user')
vi.mock('@/router', () => ({
  default: {
    push: vi.fn()
  }
}))

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
      store.user = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        full_name: 'Test User',
        is_staff: false,
        is_superuser: false,
        permissions: []
      }
      
      expect(store.userFullName).toBe('Test User')
    })

    it('userFullName returns empty string when no user', () => {
      const store = useAuthStore()
      
      expect(store.userFullName).toBe('')
    })

    it('permissions returns user permissions', () => {
      const store = useAuthStore()
      store.user = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        full_name: 'Test User',
        is_staff: false,
        is_superuser: false,
        permissions: ['view_members', 'edit_orders']
      }
      
      expect(store.permissions).toEqual(['view_members', 'edit_orders'])
    })

    it('hasPermission returns true for superuser', () => {
      const store = useAuthStore()
      store.user = {
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        full_name: 'Admin User',
        is_staff: true,
        is_superuser: true,
        permissions: []
      }
      
      expect(store.hasPermission('any_permission')).toBe(true)
    })

    it('hasPermission returns true when user has permission', () => {
      const store = useAuthStore()
      store.user = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        full_name: 'Test User',
        is_staff: false,
        is_superuser: false,
        permissions: ['view_members']
      }
      
      expect(store.hasPermission('view_members')).toBe(true)
    })

    it('hasPermission returns false when user lacks permission', () => {
      const store = useAuthStore()
      store.user = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        full_name: 'Test User',
        is_staff: false,
        is_superuser: false,
        permissions: ['view_members']
      }
      
      expect(store.hasPermission('edit_orders')).toBe(false)
    })
  })

  describe('Actions', () => {
    describe('login', () => {
      it('successfully logs in and stores tokens', async () => {
        const mockAuthResponse = {
          data: {
            access: 'new-access-token',
            refresh: 'new-refresh-token'
          }
        }
        
        const mockUserResponse = {
          data: {
            id: 1,
            username: 'testuser',
            email: 'test@example.com',
            full_name: 'Test User',
            is_staff: false,
            is_superuser: false,
            permissions: []
          }
        }
        
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
          return {
            data: {
              access: 'token',
              refresh: 'refresh'
            }
          }
        })
        
        vi.mocked(userApi.me).mockResolvedValue({
          data: {
            id: 1,
            username: 'testuser',
            email: 'test@example.com',
            full_name: 'Test User',
            is_staff: false,
            is_superuser: false,
            permissions: []
          }
        })
        
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
        store.user = {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          full_name: 'Test User',
          is_staff: false,
          is_superuser: false,
          permissions: []
        }
        
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
        
        vi.mocked(authApi.refresh).mockResolvedValue({
          data: {
            access: 'new-access-token'
          }
        })
        
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
