import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import LoginView from '../LoginView.vue'

const { login, verifyMfa, verifyMfaPasskey, replace, loginWithOidc, route, hardNavigate, store, supported } = vi.hoisted(() => ({
  login: vi.fn(), verifyMfa: vi.fn(), verifyMfaPasskey: vi.fn(), replace: vi.fn(), loginWithOidc: vi.fn(), hardNavigate: vi.fn(),
  route: { query: {} as Record<string, string> },
  store: { mfaMethods: undefined as undefined | { totp: boolean, passkey: boolean }, error: null as string | null },
  supported: { value: false },
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    login, verifyMfa, verifyMfaPasskey, loginWithOidc, mfaPending: false,
    get mfaMethods() { return store.mfaMethods },
    get error() { return store.error },
  }),
}))
vi.mock('@/utils/webauthn', () => ({ passkeysSupported: () => supported.value }))
vi.mock('@/utils/navigation', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/utils/navigation')>()),
  hardNavigate,
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ replace, currentRoute: { value: route } }) }))
vi.mock('@/api/oidc', () => ({ oidcApi: { getPublicConfig: () => Promise.resolve({ data: { enabled: false } }) } }))
vi.mock('@/api/branding', () => ({ brandingApi: { getPublicBranding: () => Promise.resolve({ data: {} }) } }))

function render() { return mount(LoginView, { global: { plugins: [PrimeVue], stubs: { RouterLink: { template: '<a><slot /></a>' } } } }) }
describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks(); route.query = {}; login.mockResolvedValue({ authenticated: true })
    store.mfaMethods = undefined; store.error = null; supported.value = false
  })
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
    login.mockImplementation(() => new Promise(resolve => { finish = () => resolve({ authenticated: true }) }))
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
  it('asks for the second factor before navigating', async () => {
    route.query = { next: '/members' }
    login.mockResolvedValue({ authenticated: false, mfa_required: true })
    verifyMfa.mockResolvedValue({ authenticated: true })
    const wrapper = render()
    await wrapper.get('#username').setValue('jugendleitung')
    await wrapper.get('#password').setValue('test-password')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(replace).not.toHaveBeenCalled()
    await wrapper.get('#mfa-code').setValue('123456')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(verifyMfa).toHaveBeenCalledWith('123456')
    expect(replace).toHaveBeenCalledWith('/members')
    wrapper.unmount()
  })
  it('sends accounts with mandatory MFA to the setup and server pages via full load', async () => {
    login.mockResolvedValueOnce({ authenticated: true, mfa_setup_required: true })
    const wrapper = render()
    await wrapper.get('#username').setValue('admin')
    await wrapper.get('#password').setValue('test-password')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(replace).toHaveBeenCalledWith('/profile?mfa=setup')
    wrapper.unmount()

    route.query = { next: '/admin/' }
    const second = render()
    await second.get('#username').setValue('admin')
    await second.get('#password').setValue('test-password')
    await second.get('form').trigger('submit')
    await flushPromises()
    expect(hardNavigate).toHaveBeenCalledWith('/admin/')
    second.unmount()
  })
  it('confirms a passkey-only account with the passkey instead of a code', async () => {
    route.query = { next: '/members' }
    supported.value = true
    login.mockImplementation(async () => {
      store.mfaMethods = { totp: false, passkey: true }
      return { authenticated: false, mfa_required: true, mfa_methods: store.mfaMethods }
    })
    verifyMfaPasskey.mockResolvedValue({ authenticated: true })
    const wrapper = render()
    await wrapper.get('#username').setValue('jugendleitung')
    await wrapper.get('#password').setValue('test-password')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('#mfa-code').exists()).toBe(false)
    const passkeyButton = wrapper.findAll('button').find(b => b.text().includes('Mit Passkey bestätigen'))!
    await passkeyButton.trigger('click')
    await flushPromises()
    expect(verifyMfaPasskey).toHaveBeenCalled()
    expect(replace).toHaveBeenCalledWith('/members')
    wrapper.unmount()
  })
  it('offers recovery codes to passkey-only accounts', async () => {
    supported.value = true
    login.mockImplementation(async () => {
      store.mfaMethods = { totp: false, passkey: true }
      return { authenticated: false, mfa_required: true }
    })
    const wrapper = render()
    await wrapper.get('#username').setValue('jugendleitung')
    await wrapper.get('#password').setValue('test-password')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    await wrapper.findAll('button').find(b => b.text() === 'Wiederherstellungscode verwenden')!.trigger('click')
    expect(wrapper.find('#mfa-code').exists()).toBe(true)
    wrapper.unmount()
  })
})
