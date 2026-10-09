import { beforeEach, describe, expect, it, vi } from 'vitest'

const { auth, settings } = vi.hoisted(() => ({
  auth: {
    isAuthenticated: true, isPortalAccount: false, mfaSetupRequired: false, isOrgWide: true, user: {},
    accountLinkPending: true, accountLinkDeferred: false,
    initialize: async () => undefined, hasPerm: () => true,
  },
  settings: { general: {}, fetchPermissions: vi.fn(), fetchCategorySettings: vi.fn(), canViewCategory: () => false, canViewAnySettings: true },
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('@/stores/settings', () => ({ useSettingsStore: () => settings }))
vi.mock('@/views/AccountLinkConfirmView.vue', () => ({ default: { template: '<p>confirm</p>' } }))
vi.mock('@/views/LoginView.vue', () => ({ default: { template: '<p>login</p>' } }))
vi.mock('@/components/layout/AppLayout.vue', () => ({ default: { template: '<div><RouterView /></div>' } }))
vi.mock('@/views/DashboardView.vue', () => ({ default: { template: '<p>dash</p>' } }))
vi.mock('@/views/MembersView.vue', () => ({ default: { template: '<p>members</p>' } }))

describe('router guard for a pending account link (PORTAL-04.2)', () => {
  beforeEach(() => {
    auth.accountLinkPending = true
    auth.accountLinkDeferred = false
    auth.mfaSetupRequired = false
  })

  it('stops at the confirmation step and keeps the target', async () => {
    const { default: router } = await import('@/router')
    await router.push('/members')
    expect(router.currentRoute.value.name).toBe('account-link-confirm')
    expect(router.currentRoute.value.query.next).toBe('/members')
  })

  it('lets the account continue after deciding or deferring', async () => {
    const { default: router } = await import('@/router')
    auth.accountLinkDeferred = true
    await router.push('/members')
    expect(router.currentRoute.value.path).toBe('/members')
    auth.accountLinkDeferred = false
    auth.accountLinkPending = false
    await router.push('/')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('lets a mandatory MFA setup go first', async () => {
    const { default: router } = await import('@/router')
    auth.mfaSetupRequired = true
    await router.push('/members')
    expect(router.currentRoute.value.path).toBe('/profile')
  })
})
