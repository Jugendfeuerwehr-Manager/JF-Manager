import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import PrimeVue from 'primevue/config'
import PortalLayout from '../PortalLayout.vue'
import PortalDataView from '../PortalDataView.vue'
import PortalPlaceholderView from '../PortalPlaceholderView.vue'
import { portalApi } from '@/api/portal'

vi.mock('@/api/portal', () => ({ portalApi: { me: vi.fn(), person: vi.fn() } }))
vi.mock('@/api/branding', () => ({ brandingApi: { getPublicBranding: vi.fn().mockResolvedValue({ data: { title: 'Jugendfeuerwehr Musterstadt', logo_url: null } }) } }))
vi.mock('@/router', () => ({ default: { push: vi.fn(), currentRoute: { value: { path: '/portal' } } } }))

const stub = { template: '<div />' }
const props = { icon: 'pi pi-calendar', title: 'Termine', text: 'x' }
const names = ['portal-home', 'portal-sessions', 'portal-data', 'portal-profile']

async function mountAt(name: string) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{
    path: '/portal', component: PortalLayout, children: [
      { path: '', name: 'portal-home', component: stub },
      { path: 'termine', name: 'portal-sessions', component: PortalPlaceholderView, props },
      { path: 'daten', name: 'portal-data', component: PortalDataView },
      { path: 'profil', name: 'portal-profile', component: stub },
    ] }] })
  await router.push({ name }); await router.isReady()
  const wrapper = mount({ template: '<RouterView />' }, { global: { plugins: [PrimeVue, router] } })
  await flushPromises()
  return wrapper
}

describe('PortalLayout', () => {
  beforeEach(() => {
    setActivePinia(createPinia()); vi.clearAllMocks()
    vi.mocked(portalApi.me).mockResolvedValue({ data: { account: { first_name: 'Anna', last_name: 'M', email: 'a@x.de' }, people: [
      { id: 1, relation: 'self', first_name: 'Anna', last_name: 'Muster' },
      { id: 2, relation: 'child', first_name: 'Tim', last_name: 'Muster' },
    ] } } as never)
    vi.mocked(portalApi.person).mockImplementation((id: number) => Promise.resolve({ data: {
      id, relation: id === 1 ? 'self' : 'child', categories: ['contact'],
      contact: { first_name: id === 1 ? 'Anna' : 'Tim', last_name: 'Muster', street: '', zip_code: '', city: '', phone: '', mobile: '', email: '' },
    } }) as never)
  })

  it('renders greeting, org name and four nav items with aria-current on the active one', async () => {
    const wrapper = await mountAt('portal-data')
    expect(wrapper.text()).toContain('Hallo Anna')
    expect(wrapper.text()).toContain('Jugendfeuerwehr Musterstadt')
    const links = wrapper.findAll('nav a')
    expect(links.map(l => l.text())).toEqual(['Übersicht', 'Termine', 'Daten', 'Profil'])
    expect(links.filter(l => l.attributes('aria-current') === 'page').map(l => l.text())).toEqual(['Daten'])
    expect(names).toHaveLength(4)
  })

  it('shows the person switcher in the header', async () => {
    const wrapper = await mountAt('portal-home')
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(2)
  })

  it('renders the Daten skeleton with disabled request button and lock hint', async () => {
    const wrapper = await mountAt('portal-data')
    expect(wrapper.text()).toContain('Name und Kontakt')
    expect(wrapper.text()).toContain('Anna Muster')
    expect(wrapper.text()).toContain('nicht einsehbar')
    expect(wrapper.find('button.request').attributes('disabled')).toBeDefined()
    await wrapper.findAll('[role="tab"]')[1]!.trigger('click')
    expect(wrapper.text()).toContain('Tim Muster')
  })

  it('renders the Termine empty state', async () => {
    const wrapper = await mountAt('portal-sessions')
    expect(wrapper.text()).toContain('Noch keine Termine')
  })
})
