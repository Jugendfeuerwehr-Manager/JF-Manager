import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import MfaSettings from '../MfaSettings.vue'

const { mfaStatus, mfaSetup } = vi.hoisted(() => ({ mfaStatus: vi.fn(), mfaSetup: vi.fn() }))
vi.mock('@/api/auth', () => ({ authApi: { mfaStatus, mfaSetup } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ mfaSetupRequired: true }) }))

const otpauthUri = 'otpauth://totp/JF-Manager:jugendleitung?secret=JBSWY3DPEHPK3PXP&issuer=JF-Manager'

describe('MfaSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mfaStatus.mockResolvedValue({ data: { enabled: false, required: true, recovery_codes_remaining: 0 } })
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
})
