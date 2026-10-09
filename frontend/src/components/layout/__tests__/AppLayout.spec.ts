import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AppLayout from '../AppLayout.vue'
import { useWorkspaceNavigation } from '@/composables/useWorkspaceNavigation'

const { auth, sessionTimeout } = vi.hoisted(() => ({
  auth: { canAccessModule: vi.fn(() => true), logout: vi.fn() },
  sessionTimeout: vi.fn(),
}))
const { inbox } = vi.hoisted(() => ({ inbox: { counts: { total: 0 }, startPolling: vi.fn(), stopPolling: vi.fn() } }))
vi.mock('@/stores/inbox', () => ({ useInboxStore: () => inbox }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => ({ activeDepartmentId: 1, departments: [{ id: 1 }] }) }))
vi.mock('@/composables/useAppSettings', () => ({ useAppSettings: () => ({ websiteTitle: 'JF-Manager' }) }))
vi.mock('@/composables/useTheme', () => ({ useTheme: () => ({ themeMode: { value: 'light' }, setMode: vi.fn() }) }))
vi.mock('@/composables/useSessionTimeout', () => ({ useSessionTimeout: sessionTimeout }))
const route = vi.hoisted(() => ({ path: '/members', meta: {} as Record<string, unknown> }))
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push: vi.fn() }) }))

const stubs = {
  StaffNotificationBell: { template: '<button class="bell-stub" />' },
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
  afterEach(() => {
    vi.clearAllMocks()
    route.path = '/members'
    route.meta = {}
    useWorkspaceNavigation().setNavHidden(false)
  })

  it('shows the active department directly in the mobile toolbar', () => {
    const wrapper = renderAt(390)
    const toolbar = wrapper.get('.mobile-toolbar')
    expect(toolbar.find('.dept-stub[data-compact="true"]').exists()).toBe(true)
    expect(toolbar.find('button[aria-label="Alle Module öffnen"]').exists()).toBe(true)
    expect(wrapper.find('.mobile-bottom-nav a[href="/members"]').attributes('aria-current')).toBe('page')
    expect(wrapper.find('.desktop-sidebar').exists()).toBe(false)
    expect(toolbar.find('.bell-stub').exists()).toBe(true)
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

  it('lets workspace views hide the desktop navigation but never other pages', () => {
    useWorkspaceNavigation().setNavHidden(true)
    expect(renderAt(1440).find('.desktop-sidebar').exists()).toBe(true)

    route.path = '/training/sessions/7/plan'
    route.meta = { workspace: true, fullWidth: true }
    const wrapper = renderAt(1440)
    expect(wrapper.find('.desktop-sidebar').exists()).toBe(false)
    expect(wrapper.get('.layout-wrapper').classes()).toContain('layout-wrapper--nav-hidden')
    expect(wrapper.get('.layout-content').classes()).toContain('layout-content--full-width')
  })
})
