import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import InvitationAcceptView from '../InvitationAcceptView.vue'
import { portalApi } from '@/api/portal'

vi.mock('@/api/portal', () => ({ portalApi: { me: vi.fn(), invitationInfo: vi.fn(), acceptInvitation: vi.fn() } }))
vi.mock('@/router', () => ({ default: { push: vi.fn(), currentRoute: { value: { path: '/passwort-festlegen' } } } }))
const push = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: { token: 'abc' } }),
  useRouter: () => ({ push }),
}))

const render = () => mount(InvitationAcceptView, {
  global: { plugins: [PrimeVue], stubs: { RouterLink: { template: '<a><slot /></a>' } } },
})
const info = { email: 'eltern@example.org', kind: 'parent', expires_at: '2030-01-01T00:00:00Z' }

describe('InvitationAcceptView', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('renders the form with the read-only e-mail', async () => {
    vi.mocked(portalApi.invitationInfo).mockResolvedValue({ data: info } as never)
    const wrapper = render(); await flushPromises()
    expect(portalApi.invitationInfo).toHaveBeenCalledWith('abc')
    const username = wrapper.get('#accept-username')
    expect((username.element as HTMLInputElement).value).toBe('eltern@example.org')
    expect(username.attributes('readonly')).toBeDefined()
    expect(wrapper.text()).toContain('Zugang einrichten')
  })

  it('shows the expired message', async () => {
    vi.mocked(portalApi.invitationInfo).mockRejectedValue({ response: { status: 410, data: { detail: 'Diese Einladung ist abgelaufen.', code: 'expired' } } })
    const wrapper = render(); await flushPromises()
    expect(wrapper.text()).toContain('Diese Einladung ist abgelaufen.')
    expect(wrapper.find('form').exists()).toBe(false)
  })

  it('shows field errors and then the success state', async () => {
    vi.mocked(portalApi.invitationInfo).mockResolvedValue({ data: info } as never)
    vi.mocked(portalApi.acceptInvitation).mockRejectedValueOnce({ response: { status: 400, data: { privacy_accepted: ['Bitte bestätigen.'] } } })
    const wrapper = render(); await flushPromises()
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.text()).toContain('Bitte bestätigen.')

    vi.mocked(portalApi.acceptInvitation).mockResolvedValueOnce({ data: { username: 'eltern@example.org' } } as never)
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.text()).toContain('Dein Zugang ist eingerichtet.')
    await wrapper.get('button').trigger('click')
    expect(push).toHaveBeenCalledWith('/login')
  })
})
