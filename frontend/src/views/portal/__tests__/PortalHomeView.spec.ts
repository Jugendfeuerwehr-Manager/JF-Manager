import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import PortalHomeView from '../PortalHomeView.vue'
import { portalApi } from '@/api/portal'

vi.mock('@/api/portal', () => ({ portalApi: { me: vi.fn() } }))
vi.mock('@/router', () => ({ default: { push: vi.fn(), currentRoute: { value: { path: '/portal' } } } }))

const render = () => mount(PortalHomeView, { global: { plugins: [PrimeVue], stubs: { RouterLink: { template: '<a><slot /></a>' } } } })
const account = { first_name: 'Anna', last_name: 'Muster', email: 'a@example.org' }

describe('PortalHomeView', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('shows the greeting and people, self as "Ich"', async () => {
    vi.mocked(portalApi.me).mockResolvedValue({ data: { account, people: [
      { id: 1, relation: 'self', first_name: 'Anna', last_name: 'Muster' },
      { id: 2, relation: 'child', first_name: 'Tim', last_name: 'Muster' },
    ] } } as never)
    const wrapper = render(); await flushPromises()
    expect(wrapper.text()).toContain('Hallo Anna')
    const chips = wrapper.findAll('.person').map(c => c.text())
    expect(chips).toEqual(['Ich', 'Tim'])
  })

  it('shows the empty state', async () => {
    vi.mocked(portalApi.me).mockResolvedValue({ data: { account, people: [] } } as never)
    const wrapper = render(); await flushPromises()
    expect(wrapper.text()).toContain('Noch keine Person mit diesem Zugang verknüpft.')
  })

  it('shows an error with retry', async () => {
    vi.mocked(portalApi.me).mockRejectedValue(new Error('x'))
    const wrapper = render(); await flushPromises()
    expect(wrapper.text()).toContain('Erneut versuchen')
  })
})
