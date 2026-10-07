import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import MfaSettings from '../MfaSettings.vue'

const { mfaStatus, mfaSetup, passkeyRegisterOptions, passkeyRegister, passkeyRemove, createPasskey, supported } = vi.hoisted(() => ({
  mfaStatus: vi.fn(), mfaSetup: vi.fn(), passkeyRegisterOptions: vi.fn(), passkeyRegister: vi.fn(), passkeyRemove: vi.fn(),
  createPasskey: vi.fn(), supported: { value: false },
}))
vi.mock('@/api/auth', () => ({ authApi: { mfaStatus, mfaSetup, passkeyRegisterOptions, passkeyRegister, passkeyRemove } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ mfaSetupRequired: true, refreshSession: vi.fn() }) }))
vi.mock('@/utils/webauthn', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/utils/webauthn')>()),
  createPasskey,
  passkeysSupported: () => supported.value,
}))

const noMfa = { enabled: false, totp_enabled: false, passkeys: [], required: true, recovery_codes_remaining: 0, setup_pending: false }
const laptop = { id: 3, name: 'Laptop', created_at: '2026-10-01T10:00:00Z', last_used_at: null, backed_up: true }

const otpauthUri = 'otpauth://totp/JF-Manager:jugendleitung?secret=JBSWY3DPEHPK3PXP&issuer=JF-Manager'

describe('MfaSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    supported.value = false
    mfaStatus.mockResolvedValue({ data: noMfa })
    mfaSetup.mockResolvedValue({ data: { secret: 'JBSWY3DPEHPK3PXP', otpauth_uri: otpauthUri } })
  })

  it('shows a locally rendered QR code for the authenticator setup', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
    const wrapper = mount(MfaSettings, { props: { setupRequested: true }, global: { plugins: [PrimeVue] } })
    await flushPromises()
    await vi.waitFor(() => expect(wrapper.find('img.qr-code').exists()).toBe(true))

    const img = wrapper.get('img.qr-code')
    expect(img.attributes('alt')).toContain('QR-Code')
    const src = img.attributes('src') ?? ''
    expect(src.startsWith('data:image/svg+xml')).toBe(true)
    expect(decodeURIComponent(src)).toContain('<svg')
    expect(fetchSpy).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('JBSW Y3DP EHPK 3PXP')

    await wrapper.get('button[type="button"]').trigger('click')
    expect(wrapper.find('img.qr-code').exists()).toBe(false)
    wrapper.unmount()
  })

  it('adds a passkey and shows the recovery codes of the first factor', async () => {
    supported.value = true
    passkeyRegisterOptions.mockResolvedValue({ data: { challenge: 'AQID' } })
    createPasskey.mockResolvedValue({ id: 'cred' })
    passkeyRegister.mockResolvedValue({
      data: { ...noMfa, enabled: true, passkeys: [laptop], recovery_codes_remaining: 10, recovery_codes: ['aaaa-bbbb-cccc'] },
    })
    const wrapper = mount(MfaSettings, { props: { setupRequested: true }, global: { plugins: [PrimeVue] } })
    await flushPromises()
    // With passkey support the person chooses; no automatic app setup.
    expect(mfaSetup).not.toHaveBeenCalled()
    await wrapper.get('#passkey-name').setValue('Laptop')
    await wrapper.get('form.inline-form').trigger('submit')
    await flushPromises()
    expect(createPasskey).toHaveBeenCalledWith({ challenge: 'AQID' })
    expect(passkeyRegister).toHaveBeenCalledWith({ id: 'cred' }, 'Laptop')
    expect(wrapper.text()).toContain('aaaa-bbbb-cccc')
    wrapper.unmount()
  })

  it('keeps the last factor of a mandatory account', async () => {
    supported.value = true
    mfaStatus.mockResolvedValue({ data: { ...noMfa, enabled: true, passkeys: [laptop], recovery_codes_remaining: 10 } })
    const wrapper = mount(MfaSettings, { global: { plugins: [PrimeVue] } })
    await flushPromises()
    const remove = wrapper.get('button[aria-label="Passkey Laptop entfernen"]')
    expect(remove.attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('letzte zweite Faktor')
    wrapper.unmount()
  })

  it('removes a passkey when another factor remains', async () => {
    supported.value = true
    const status = { ...noMfa, enabled: true, totp_enabled: true, passkeys: [laptop], recovery_codes_remaining: 10 }
    mfaStatus.mockResolvedValue({ data: status })
    passkeyRemove.mockResolvedValue({ data: { ...status, passkeys: [] } })
    const wrapper = mount(MfaSettings, { global: { plugins: [PrimeVue] } })
    await flushPromises()
    await wrapper.get('button[aria-label="Passkey Laptop entfernen"]').trigger('click')
    await flushPromises()
    expect(passkeyRemove).toHaveBeenCalledWith(3)
    expect(wrapper.text()).toContain('Noch kein Passkey')
    wrapper.unmount()
  })
})
