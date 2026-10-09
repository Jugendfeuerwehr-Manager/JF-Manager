import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import PortalHomeView from '../PortalHomeView.vue'
import { portalApi } from '@/api/portal'
import { usePortalStore } from '@/stores/portal'

vi.mock('@/api/portal', () => ({ portalApi: { me: vi.fn(), sessions: vi.fn() } }))
vi.mock('@/router', () => ({ default: { push: vi.fn(), currentRoute: { value: { path: '/portal' } } } }))

const render = () => mount(PortalHomeView, { global: { plugins: [PrimeVue], stubs: { RouterLink: { template: '<a><slot /></a>' } } } })
const account = { first_name: 'Anna', last_name: 'Muster', email: 'a@example.org' }

describe('PortalHomeView', () => {
  beforeEach(() => {
    setActivePinia(createPinia()); vi.clearAllMocks()
    vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 1, sessions: [] } } as never)
  })

  it('shows the empty services card for the selected person', async () => {
    vi.mocked(portalApi.me).mockResolvedValue({ data: { account, people: [
      { id: 1, relation: 'self', first_name: 'Anna', last_name: 'Muster' },
      { id: 2, relation: 'child', first_name: 'Tim', last_name: 'Muster' },
    ] } } as never)
    const wrapper = render(); await flushPromises()
    expect(wrapper.text()).toContain('Nächste Dienste')
    expect(wrapper.text()).toContain('Noch keine geplanten Dienste')
    expect(wrapper.text()).toContain('für dich')
    usePortalStore().selectPerson(2); await flushPromises()
    expect(wrapper.text()).toContain('für Tim')
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
