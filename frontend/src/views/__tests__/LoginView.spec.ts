import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import LoginView from '../LoginView.vue'

const { login, replace, loginWithOidc, route } = vi.hoisted(() => ({
  login: vi.fn(), replace: vi.fn(), loginWithOidc: vi.fn(), route: { query: {} as Record<string, string> },
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ login, loginWithOidc }) }))
vi.mock('vue-router', () => ({ useRouter: () => ({ replace, currentRoute: { value: route } }) }))
vi.mock('@/api/oidc', () => ({ oidcApi: { getPublicConfig: () => Promise.resolve({ data: { enabled: false } }) } }))
vi.mock('@/api/branding', () => ({ brandingApi: { getPublicBranding: () => Promise.resolve({ data: {} }) } }))

function render() { return mount(LoginView, { global: { plugins: [PrimeVue], stubs: { RouterLink: { template: '<a><slot /></a>' } } } }) }
describe('Login', () => {
  beforeEach(() => { vi.clearAllMocks(); route.query = {}; login.mockResolvedValue(true) })
  it('navigates immediately after authentication and preserves a local destination', async () => {
    route.query = { next: '/servicebook' }
    const wrapper = render()
    await wrapper.get('#username').setValue('jugendleitung')
    await wrapper.get('#password').setValue('test-password')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(login).toHaveBeenCalledWith('jugendleitung', 'test-password')
    expect(replace).toHaveBeenCalledWith('/servicebook')
    wrapper.unmount()
  })
  it('prevents duplicate submissions while authentication is pending', async () => {
    let finish!: () => void
    login.mockImplementation(() => new Promise<void>(resolve => { finish = resolve }))
    const wrapper = render()
    await wrapper.get('#username').setValue('jugendleitung')
    await wrapper.get('#password').setValue('test-password')
    await wrapper.get('form').trigger('submit')
    await wrapper.get('form').trigger('submit')
    expect(login).toHaveBeenCalledTimes(1)
    expect(replace).not.toHaveBeenCalled()
    finish()
    await flushPromises()
    wrapper.unmount()
  })
  it('rejects external return destinations', async () => {
    route.query = { next: '//example.org' }
    const wrapper = render()
    await wrapper.get('#username').setValue('jugendleitung')
    await wrapper.get('#password').setValue('test-password')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(replace).toHaveBeenCalledWith('/')
    wrapper.unmount()
  })
})
