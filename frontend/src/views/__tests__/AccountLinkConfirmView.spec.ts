import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import AccountLinkConfirmView from '../AccountLinkConfirmView.vue'
import { accountLinksApi } from '@/api/accountLinks'

const { auth, replace } = vi.hoisted(() => ({
  auth: { refreshSession: vi.fn(async () => undefined), deferAccountLink: vi.fn() },
  replace: vi.fn(),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('vue-router', () => ({ useRoute: () => ({ query: { next: '/members' } }), useRouter: () => ({ replace }) }))
vi.mock('@/api/accountLinks', () => ({
  accountLinksApi: { pendingForMe: vi.fn(), confirm: vi.fn(), reject: vi.fn() },
}))
const api = vi.mocked(accountLinksApi)

const link = {
  id: 4, status: 'pending', user: { id: 2, username: 'leitung', name: 'Tobias Lehmann' },
  member: { id: 9, name: 'Tobias Lehmann', birth_year: 1990, departments: ['Mitte'], group: null },
  parent: { id: 3, name: 'Tobias Lehmann', children: [{ first_name: 'Ella', group: 'Gruppe 1' }] },
  linked_by: 'Alex Sommer', linked_at: '', confirmed_at: null, rejected_at: null,
}

function render() {
  return mount(AccountLinkConfirmView, { global: { plugins: [PrimeVue] } })
}

describe('AccountLinkConfirmView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.pendingForMe.mockResolvedValue({ data: { link } } as never)
  })

  it('shows member and parent record with year, department, group and children', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Sind das deine Datensätze?')
    expect(wrapper.text()).toContain('1990')
    expect(wrapper.text()).toContain('Mitte')
    expect(wrapper.text()).toContain('Ella (Gruppe 1)')
    expect(wrapper.text()).toContain('Alex Sommer')
  })

  it('confirms, refreshes the session and continues to the target', async () => {
    api.confirm.mockResolvedValue({ data: { ...link, status: 'confirmed' } } as never)
    const wrapper = render()
    await flushPromises()
    await wrapper.findAll('button').find(b => b.text().includes('Ja, das bin ich'))!.trigger('click')
    await flushPromises()
    expect(api.confirm).toHaveBeenCalledWith(4)
    expect(auth.refreshSession).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Verknüpfung bestätigt')
    await wrapper.findAll('button').find(b => b.text().includes('Weiter'))!.trigger('click')
    expect(replace).toHaveBeenCalledWith('/members')
  })

  it('rejects with a note that the linking person is informed', async () => {
    api.reject.mockResolvedValue({ data: { ...link, status: 'rejected' } } as never)
    const wrapper = render()
    await flushPromises()
    await wrapper.findAll('button').find(b => b.text().includes('Nein, nicht meiner'))!.trigger('click')
    await flushPromises()
    expect(api.reject).toHaveBeenCalledWith(4)
    expect(wrapper.text()).toContain('erhält einen Hinweis')
  })

  it('shows the server error and keeps the choice open', async () => {
    api.confirm.mockRejectedValue(Object.assign(new Error('x'), { response: { status: 409, data: { detail: 'Bereits entschieden.' } } }))
    const wrapper = render()
    await flushPromises()
    await wrapper.findAll('button').find(b => b.text().includes('Ja, das bin ich'))!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Bereits entschieden.')
    expect(wrapper.text()).toContain('Nein, nicht meiner')
  })

  it('defers the decision for this session', async () => {
    const wrapper = render()
    await flushPromises()
    await wrapper.find('button.later').trigger('click')
    expect(auth.deferAccountLink).toHaveBeenCalled()
    expect(replace).toHaveBeenCalledWith('/members')
  })
})
