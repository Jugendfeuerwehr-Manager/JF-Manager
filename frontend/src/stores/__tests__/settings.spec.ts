import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSettingsStore } from '../settings'
import { settingsApi } from '@/api/settings'
import type {
  GeneralSettings,
  EmailSettings,
  OrderSettings,
  SettingsPermissions
} from '@/types/settings'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'

// Mock API module
vi.mock('@/api/settings')

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

describe('Settings Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  const mockGeneralSettings: GeneralSettings = {
    title: 'JF-Manager Test'
  }

  const mockEmailSettings: EmailSettings = {
    email_host: 'smtp.example.com',
    email_port: 587,
    email_use_tls: true,
    email_use_ssl: false,
    email_host_user: 'user@example.com',
    default_from_email: 'noreply@example.com'
  }

  const mockOrderSettings: OrderSettings = {
    equipment_manager_email: 'manager@example.com'
  }

  const mockPermissions: SettingsPermissions = {
    can_view_all: false,
    can_change_all: false,
    categories: {
      general: { can_view: true, can_change: false },
      email: { can_view: true, can_change: true },
      member: { can_view: true, can_change: false },
      service: { can_view: false, can_change: false },
      order: { can_view: true, can_change: true },
      ldap: { can_view: false, can_change: false }
    }
  }

  describe('State', () => {
    it('initializes with null settings', () => {
      const store = useSettingsStore()
      
      expect(store.general).toBeNull()
      expect(store.email).toBeNull()
      expect(store.member).toBeNull()
      expect(store.service).toBeNull()
      expect(store.order).toBeNull()
      expect(store.permissions).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('Computed', () => {
    it('hasPermissions returns true when permissions loaded', () => {
      const store = useSettingsStore()
      store.permissions = mockPermissions
      
      expect(store.hasPermissions).toBe(true)
    })

    it('hasPermissions returns false when no permissions', () => {
      const store = useSettingsStore()
      
      expect(store.hasPermissions).toBe(false)
    })

    it('canViewAnySettings returns true when can_view_all', () => {
      const store = useSettingsStore()
      store.permissions = {
        ...mockPermissions,
        can_view_all: true
      }
      
      expect(store.canViewAnySettings).toBe(true)
    })

    it('canViewAnySettings returns true when can view any category', () => {
      const store = useSettingsStore()
      store.permissions = mockPermissions
      
      expect(store.canViewAnySettings).toBe(true)
    })

    it('canViewCategory returns correct permissions', () => {
      const store = useSettingsStore()
      store.permissions = mockPermissions
      
      expect(store.canViewCategory('general')).toBe(true)
      expect(store.canViewCategory('service')).toBe(false)
    })

    it('canChangeCategory returns correct permissions', () => {
      const store = useSettingsStore()
      store.permissions = mockPermissions
      
      expect(store.canChangeCategory('email')).toBe(true)
      expect(store.canChangeCategory('general')).toBe(false)
    })

    it('equipmentManagerEmail returns email from order settings', () => {
      const store = useSettingsStore()
      store.order = mockOrderSettings
      
      expect(store.equipmentManagerEmail).toBe('manager@example.com')
    })

    it('equipmentManagerEmail returns empty string when no order settings', () => {
      const store = useSettingsStore()
      
      expect(store.equipmentManagerEmail).toBe('')
    })

    it('availableTabs filters tabs by permissions', () => {
      const store = useSettingsStore()
      store.permissions = mockPermissions
      
      const tabs = store.availableTabs
      
      // Should have general, email, member, order tabs (service excluded)
      expect(tabs.length).toBe(5) // 4 categories + email-templates
      expect(tabs.find(t => t.id === 'general')).toBeDefined()
      expect(tabs.find(t => t.id === 'email')).toBeDefined()
      expect(tabs.find(t => t.id === 'member')).toBeDefined()
      expect(tabs.find(t => t.id === 'order')).toBeDefined()
      expect(tabs.find(t => t.id === 'service')).toBeUndefined()
    })
  })

  describe('Actions', () => {
    describe('fetchPermissions', () => {
      it('fetches permissions successfully', async () => {
        const mockResponse = createMockAxiosResponse(mockPermissions)
        
        vi.mocked(settingsApi.getPermissions).mockResolvedValue(mockResponse)
        
        const store = useSettingsStore()
        const result = await store.fetchPermissions()
        
        expect(result).toEqual(mockPermissions)
        expect(store.permissions).toEqual(mockPermissions)
        expect(store.loading).toBe(false)
      })

      it('handles fetch error', async () => {
        vi.mocked(settingsApi.getPermissions).mockRejectedValue(new Error('Network error'))
        
        const store = useSettingsStore()
        
        await expect(store.fetchPermissions()).rejects.toThrow()
        expect(store.error).toBeTruthy()
      })
    })

    describe('fetchAllSettings', () => {
      it('fetches all settings successfully', async () => {
        const mockResponse = createMockAxiosResponse({
          general: mockGeneralSettings,
          email: mockEmailSettings,
          order: mockOrderSettings
        })
        
        vi.mocked(settingsApi.getAll).mockResolvedValue(mockResponse)
        
        const store = useSettingsStore()
        await store.fetchAllSettings()
        
        expect(store.general).toEqual(mockGeneralSettings)
        expect(store.email).toEqual(mockEmailSettings)
        expect(store.order).toEqual(mockOrderSettings)
      })
    })

    describe('fetchCategorySettings', () => {
      it('fetches general settings', async () => {
        const mockResponse = createMockAxiosResponse(mockGeneralSettings)
        
        vi.mocked(settingsApi.getByCategory).mockResolvedValue(mockResponse)
        
        const store = useSettingsStore()
        await store.fetchCategorySettings('general')
        
        expect(store.general).toEqual(mockGeneralSettings)
        expect(settingsApi.getByCategory).toHaveBeenCalledWith('general')
      })

      it('fetches email settings', async () => {
        const mockResponse = createMockAxiosResponse(mockEmailSettings)
        
        vi.mocked(settingsApi.getByCategory).mockResolvedValue(mockResponse)
        
        const store = useSettingsStore()
        await store.fetchCategorySettings('email')
        
        expect(store.email).toEqual(mockEmailSettings)
      })

      it('fetches order settings', async () => {
        const mockResponse = createMockAxiosResponse(mockOrderSettings)
        
        vi.mocked(settingsApi.getByCategory).mockResolvedValue(mockResponse)
        
        const store = useSettingsStore()
        await store.fetchCategorySettings('order')
        
        expect(store.order).toEqual(mockOrderSettings)
      })
    })

    describe('updateCategorySettings', () => {
      it('updates general settings', async () => {
        const updatedSettings = { title: 'New Title' }
        const mockResponse = createMockAxiosResponse(updatedSettings as GeneralSettings)
        
        vi.mocked(settingsApi.updateByCategory).mockResolvedValue(mockResponse)
        
        const store = useSettingsStore()
        await store.updateCategorySettings('general', updatedSettings)
        
        expect(store.general).toEqual(updatedSettings)
        expect(settingsApi.updateByCategory).toHaveBeenCalledWith('general', updatedSettings)
      })

      it('updates email settings', async () => {
        const updatedSettings = { email_host: 'smtp.new.com' }
        const mockResponse = createMockAxiosResponse({ ...mockEmailSettings, ...updatedSettings })
        
        vi.mocked(settingsApi.updateByCategory).mockResolvedValue(mockResponse)
        
        const store = useSettingsStore()
        await store.updateCategorySettings('email', updatedSettings)
        
        expect(store.email).toEqual(mockResponse.data)
      })
    })

    describe('updateGeneral', () => {
      it('calls updateCategorySettings with general category', async () => {
        const updatedSettings = { title: 'Updated' }
        const mockResponse = createMockAxiosResponse(updatedSettings as GeneralSettings)
        
        vi.mocked(settingsApi.updateByCategory).mockResolvedValue(mockResponse)
        
        const store = useSettingsStore()
        await store.updateGeneral(updatedSettings)
        
        expect(settingsApi.updateByCategory).toHaveBeenCalledWith(
          'general',
          expect.objectContaining(updatedSettings)
        )
      })
    })

    describe('clearError', () => {
      it('clears error state', () => {
        const store = useSettingsStore()
        store.error = 'Some error'
        
        store.clearError()
        
        expect(store.error).toBeNull()
      })
    })

    describe('$reset', () => {
      it('resets store to initial state', () => {
        const store = useSettingsStore()
        store.general = mockGeneralSettings
        store.email = mockEmailSettings
        store.permissions = mockPermissions
        store.error = 'error'
        
        store.$reset()
        
        expect(store.general).toBeNull()
        expect(store.email).toBeNull()
        expect(store.permissions).toBeNull()
        expect(store.error).toBeNull()
      })
    })
  })
})
