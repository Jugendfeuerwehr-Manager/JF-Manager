import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import LoginView from '../LoginView.vue'

const { login, verifyMfa, verifyMfaPasskey, signInWithPasskey, replace, loginWithOidc, route, hardNavigate, store, supported } = vi.hoisted(() => ({
  login: vi.fn(), verifyMfa: vi.fn(), verifyMfaPasskey: vi.fn(), signInWithPasskey: vi.fn(), replace: vi.fn(), loginWithOidc: vi.fn(), hardNavigate: vi.fn(),
  route: { query: {} as Record<string, string> },
  store: { mfaMethods: undefined as undefined | { totp: boolean, passkey: boolean }, error: null as string | null },
  supported: { value: false },
}))
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    login, verifyMfa, verifyMfaPasskey, signInWithPasskey, loginWithOidc, mfaPending: false,
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
const { branding } = vi.hoisted(() => ({ branding: { data: {} as Record<string, unknown> } }))
vi.mock('@/api/branding', () => ({ brandingApi: { getPublicBranding: () => Promise.resolve(branding) } }))

function render() { return mount(LoginView, { global: { plugins: [PrimeVue], stubs: { RouterLink: { template: '<a><slot /></a>' } } } }) }
describe('Login', () => {
  beforeEach(() => {
    vi.clearAllMocks(); route.query = {}; login.mockResolvedValue({ authenticated: true })
    store.mfaMethods = undefined; store.error = null; supported.value = false; branding.data = {}
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
  it('signs in with a passkey alone, without username or password', async () => {
    supported.value = true
    route.query = { next: '/servicebook' }
    signInWithPasskey.mockResolvedValue({ authenticated: true })
    const wrapper = render()
    await wrapper.findAll('button').find(b => b.text().includes('Mit Passkey anmelden'))!.trigger('click')
    await flushPromises()
    expect(signInWithPasskey).toHaveBeenCalledTimes(1)
    expect(login).not.toHaveBeenCalled()
    expect(replace).toHaveBeenCalledWith('/servicebook')
    wrapper.unmount()
  })
  it('shows the passkey error and keeps the password form available', async () => {
    supported.value = true
    signInWithPasskey.mockImplementation(() => { store.error = 'Der Passkey-Vorgang wurde abgebrochen oder ist abgelaufen.'; return Promise.reject(new Error('cancelled')) })
    const wrapper = render()
    await wrapper.findAll('button').find(b => b.text().includes('Mit Passkey anmelden'))!.trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('abgebrochen')
    expect(wrapper.find('#password').exists()).toBe(true)
    expect(replace).not.toHaveBeenCalled()
    wrapper.unmount()
  })
  it('hides the passkey sign-in where the browser cannot use passkeys', () => {
    const wrapper = render()
    expect(wrapper.findAll('button').some(b => b.text().includes('Mit Passkey anmelden'))).toBe(false)
    wrapper.unmount()
  })
  it('shows the configured login texts as plain text and hides empty ones', async () => {
    branding.data = { title: 'SV Muster', login_texts: { eyebrow: '<b>Verein</b>', headline: 'Willkommen\nim Verein', intro: 'Alles an einem Ort.', footer: '', help: 'Zugang beim Vorstand anfragen.' } }
    const wrapper = render()
    await flushPromises()
    expect(wrapper.get('.intro-copy .eyebrow').text()).toBe('<b>Verein</b>')
    expect(wrapper.find('.intro-copy .eyebrow b').exists()).toBe(false)
    expect(wrapper.get('h1').element.textContent).toBe('Willkommen\nim Verein')
    expect(wrapper.find('.intro-footer').exists()).toBe(false)
    expect(wrapper.get('.login-help').text()).toBe('Zugang beim Vorstand anfragen.')
    wrapper.unmount()
  })
  it('keeps the default texts when branding cannot be loaded', () => {
    const wrapper = render()
    expect(wrapper.get('h1').text()).toContain('Mehr Zeit für')
    expect(wrapper.get('.login-help').text()).toContain('Noch keinen Zugang?')
    wrapper.unmount()
  })
})
