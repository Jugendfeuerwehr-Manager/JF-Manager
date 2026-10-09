import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PortalPersonSwitcher from '../PortalPersonSwitcher.vue'
import { portalApi } from '@/api/portal'
import { usePortalStore } from '@/stores/portal'

vi.mock('@/api/portal', () => ({ portalApi: { me: vi.fn() } }))
vi.mock('@/router', () => ({ default: { push: vi.fn(), currentRoute: { value: { path: '/portal' } } } }))

const account = { first_name: 'Anna', last_name: 'Muster', email: 'a@example.org' }
const self = { id: 1, relation: 'self', first_name: 'Anna', last_name: 'Muster' }
const child = { id: 2, relation: 'child', first_name: 'Tim', last_name: 'Muster' }

describe('PortalPersonSwitcher', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('is hidden for a single person', async () => {
    vi.mocked(portalApi.me).mockResolvedValue({ data: { account, people: [child] } } as never)
    await usePortalStore().fetchMe()
    expect(mount(PortalPersonSwitcher).find('[role="tablist"]').exists()).toBe(false)
  })

  it('renders tabs, selects the first and persists the selection in the store', async () => {
    vi.mocked(portalApi.me).mockResolvedValue({ data: { account, people: [self, child] } } as never)
    const store = usePortalStore(); await store.fetchMe()
    const wrapper = mount(PortalPersonSwitcher); await flushPromises()
    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs.map(t => t.text())).toEqual(['Ich', 'TM Tim'])
    expect(tabs[0]!.attributes('aria-selected')).toBe('true')
    await tabs[1]!.trigger('click')
    expect(store.selectedPersonId).toBe(2)
    expect(wrapper.findAll('[role="tab"]')[1]!.attributes('aria-selected')).toBe('true')
    await store.fetchMe()
    expect(store.selectedPersonId).toBe(2)
  })

  it('shows "Vorname · Alter" only when the age is released', async () => {
    vi.mocked(portalApi.me).mockResolvedValue({ data: { account, people: [self, { ...child, age: 12 }, { id: 3, relation: 'child', first_name: 'Jo', last_name: 'Muster' }] } } as never)
    await usePortalStore().fetchMe()
    const tabs = mount(PortalPersonSwitcher).findAll('[role="tab"]')
    expect(tabs.map(t => t.text())).toEqual(['Ich', 'TM Tim · 12', 'JM Jo'])
  })
})
