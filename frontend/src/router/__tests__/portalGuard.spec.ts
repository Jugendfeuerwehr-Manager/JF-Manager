import { beforeEach, describe, expect, it, vi } from 'vitest'

const { auth, settings } = vi.hoisted(() => ({
  auth: { isAuthenticated: true, isPortalAccount: false, mfaSetupRequired: false, isOrgWide: true, user: {}, initialize: async () => undefined, hasPerm: () => true },
  settings: { general: {}, fetchPermissions: vi.fn(), fetchCategorySettings: vi.fn(), canViewCategory: () => false, canViewAnySettings: true },
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('@/stores/settings', () => ({ useSettingsStore: () => settings }))
vi.mock('@/views/portal/PortalLayout.vue', () => ({ default: { template: '<div><RouterView /></div>' } }))
vi.mock('@/views/portal/PortalHomeView.vue', () => ({ default: { template: '<p>home</p>' } }))
vi.mock('@/views/portal/PortalProfileView.vue', () => ({ default: { template: '<p>profile</p>' } }))
vi.mock('@/views/portal/PortalPlaceholderView.vue', () => ({ default: { template: '<p>p</p>' } }))
vi.mock('@/views/LoginView.vue', () => ({ default: { template: '<p>login</p>' } }))
vi.mock('@/components/layout/AppLayout.vue', () => ({ default: { template: '<div><RouterView /></div>' } }))
vi.mock('@/views/DashboardView.vue', () => ({ default: { template: '<p>dash</p>' } }))
vi.mock('@/views/MembersView.vue', () => ({ default: { template: '<p>members</p>' } }))

describe('router guard for portal accounts', () => {
  beforeEach(() => { auth.isAuthenticated = true; auth.isPortalAccount = false; vi.clearAllMocks() })

  it('sends portal accounts from staff routes and login to /portal without loading settings', async () => {
    auth.isPortalAccount = true
    settings.general = null as unknown as object
    const { default: router } = await import('@/router')
    await router.push('/members')
    expect(router.currentRoute.value.path).toBe('/portal')
    await router.push('/login')
    expect(router.currentRoute.value.path).toBe('/portal')
    await router.push('/portal/termine')
    expect(router.currentRoute.value.name).toBe('portal-sessions')
    expect(settings.fetchPermissions).not.toHaveBeenCalled()
  })

  it('sends staff accounts away from portal routes', async () => {
    const { default: router } = await import('@/router')
    await router.push('/portal/profil')
    expect(router.currentRoute.value.path).toBe('/')
  })
})
