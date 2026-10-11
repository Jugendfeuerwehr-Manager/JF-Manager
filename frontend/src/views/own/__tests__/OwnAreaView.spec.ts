import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import OwnAreaView from '../OwnAreaView.vue'
import { portalApi } from '@/api/portal'
import { accountLinksApi } from '@/api/accountLinks'
import { usePortalStore } from '@/stores/portal'

const { auth } = vi.hoisted(() => ({ auth: { linkedPerson: { member: true, children: true } } }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('@/api/portal', () => ({
  portalApi: { useBase: vi.fn(), me: vi.fn(), person: vi.fn(), sessions: vi.fn() },
}))
vi.mock('@/api/accountLinks', () => ({ accountLinksApi: { requestRelease: vi.fn() } }))
const api = vi.mocked(portalApi)

const me = {
  account: { first_name: 'Tobias', last_name: 'Lehmann', email: '' },
  people: [
    { id: 1, relation: 'self', first_name: 'Tobias', last_name: 'Lehmann' },
    { id: 2, relation: 'child', first_name: 'Ella', last_name: 'Lehmann', age: 12 },
    { id: 3, relation: 'child', first_name: 'Ben', last_name: 'Lehmann', age: 9 },
  ],
  can_edit: { member: true, parent: true },
  evidence_notice: 'Nachweise pflegt eine andere Person.',
}

function render(section: 'dienste' | 'daten' | 'kinder') {
  return mount(OwnAreaView, {
    props: { section },
    global: {
      plugins: [PrimeVue],
      stubs: {
        RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
        PortalSessionList: { template: '<div class="sessions-stub" />' },
        OwnDataPanel: { props: ['relation'], template: '<div class="data-stub">{{ relation }}</div>' },
      },
    },
  })
}

describe('OwnAreaView (PORTAL-04.3)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    auth.linkedPerson = { member: true, children: true }
    api.me.mockResolvedValue({ data: me } as never)
    api.person.mockResolvedValue({ data: { id: 1, relation: 'self', categories: [], contact: {} } } as never)
  })

  it('switches the person calls to /my/ and shows the own services', async () => {
    const wrapper = render('dienste')
    await flushPromises()
    expect(api.useBase).toHaveBeenCalledWith('/my')
    expect(usePortalStore().selectedPersonId).toBe(1)
    expect(wrapper.text()).toContain('Meine nächsten Dienste')
    expect(wrapper.find('.sessions-stub').exists()).toBe(true)
    expect(wrapper.findAll('nav a').map(a => a.attributes('href'))).toEqual(['/ich/dienste', '/ich/daten', '/ich/kinder'])
  })

  it('offers only the children in the children section', async () => {
    const wrapper = render('kinder')
    await flushPromises()
    const chips = wrapper.findAll('[role="tab"]')
    expect(chips.map(c => c.text())).toEqual(['Ella · 12', 'Ben · 9'])
    expect(usePortalStore().selectedPersonId).toBe(2)
    await chips[1]!.trigger('click')
    expect(usePortalStore().selectedPersonId).toBe(3)
    expect(wrapper.text()).toContain('Dienste von Ben')
    expect(api.person).toHaveBeenCalledWith(3)
  })

  it('asks account management to release the link from the data section', async () => {
    vi.mocked(accountLinksApi.requestRelease).mockResolvedValue({ data: { requested: true, new: true } } as never)
    const wrapper = render('daten')
    await flushPromises()
    expect(wrapper.find('.data-stub').text()).toBe('self')
    await wrapper.findAll('button').find(b => b.text().includes('Lösen beantragen'))!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Antrag gesendet')
  })

  it('explains an empty children section', async () => {
    api.me.mockResolvedValue({ data: { ...me, people: [me.people[0]] } } as never)
    const wrapper = render('kinder')
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Kinder verknüpft')
  })
})
