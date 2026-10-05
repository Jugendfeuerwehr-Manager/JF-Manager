import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AppLayout from '../AppLayout.vue'

const { auth, sessionTimeout } = vi.hoisted(() => ({
  auth: { canAccessModule: vi.fn(() => true), logout: vi.fn() },
  sessionTimeout: vi.fn(),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => ({ activeDepartmentId: 1, departments: [{ id: 1 }] }) }))
vi.mock('@/composables/useAppSettings', () => ({ useAppSettings: () => ({ websiteTitle: 'JF-Manager' }) }))
vi.mock('@/composables/useTheme', () => ({ useTheme: () => ({ themeMode: { value: 'light' }, setMode: vi.fn() }) }))
vi.mock('@/composables/useSessionTimeout', () => ({ useSessionTimeout: sessionTimeout }))
vi.mock('vue-router', () => ({ useRoute: () => ({ path: '/members' }), useRouter: () => ({ push: vi.fn() }) }))

const stubs = {
  AppTopbar: { template: '<div class="topbar-stub" />' },
  ModuleNavigation: { template: '<nav class="module-nav-stub" />' },
  DepartmentSwitcher: { props: { compact: Boolean }, template: '<div class="dept-stub" :data-compact="compact" />' },
  Drawer: { template: '<div><slot name="header" /><slot /></div>' },
  ConfirmDialog: { props: ['group'], template: '<div class="confirm-stub" :data-group="group" />' },
  Menu: { template: '<div />' },
  RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
  RouterView: { template: '<div />' },
}

function renderAt(width: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: width })
  return mount(AppLayout, { global: { stubs } })
}

describe('App layout shell', () => {
  afterEach(() => { vi.clearAllMocks() })

  it('shows the active department directly in the mobile toolbar', () => {
    const wrapper = renderAt(390)
    const toolbar = wrapper.get('.mobile-toolbar')
    expect(toolbar.find('.dept-stub[data-compact="true"]').exists()).toBe(true)
    expect(toolbar.find('button[aria-label="Alle Module öffnen"]').exists()).toBe(true)
    expect(wrapper.find('.mobile-bottom-nav a[href="/members"]').attributes('aria-current')).toBe('page')
    expect(wrapper.find('.desktop-sidebar').exists()).toBe(false)
  })

  it('keeps a permanent navigation on desktop', () => {
    const wrapper = renderAt(1440)
    expect(wrapper.find('.topbar-stub').exists()).toBe(true)
    expect(wrapper.find('.desktop-sidebar .module-nav-stub').exists()).toBe(true)
    expect(wrapper.find('.mobile-toolbar').exists()).toBe(false)
  })

  it('keeps the session expiry warning and the skip link', () => {
    const wrapper = renderAt(1440)
    expect(sessionTimeout).toHaveBeenCalledOnce()
    expect(wrapper.find('.confirm-stub[data-group="session-timeout"]').exists()).toBe(true)
    expect(wrapper.get('.skip-link').attributes('href')).toBe('#main-content')
  })
})
