import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import GroupManagementView from '../GroupManagementView.vue'

const { store, route, replace } = vi.hoisted(() => ({
  store: {
    groups: [] as { id: number; name: string }[],
    members: [] as unknown[],
    loading: false,
    saving: false,
    fetchGroups: vi.fn(),
    fetchAllMembers: vi.fn(),
    createGroup: vi.fn(),
    updateGroup: vi.fn(),
    deleteGroup: vi.fn(),
    assignMember: vi.fn(),
  },
  route: { query: {} as Record<string, string> },
  replace: vi.fn(),
}))
vi.mock('@/stores/groups', () => ({ useGroupsStore: () => store }))
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ replace, push: vi.fn() }) }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: vi.fn() }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))
vi.mock('@/composables/usePrivateMedia', () => ({ usePrivateMedia: () => ({ value: undefined }) }))

const member = (id: number, name: string, groupId: number | null) => ({
  id, name, lastname: 'Muster', full_name: `${name} Muster`, avatar_url: null,
  status: { id: 1, name: 'Aktiv', color: '#2e7d32' },
  group: groupId ? { id: groupId, name: `Gruppe ${groupId}` } : null,
})

function render() {
  return mount(GroupManagementView, {
    attachTo: document.body,
    global: { plugins: [PrimeVue], directives: { tooltip: () => {} }, stubs: { Dialog: { template: '<div class="dialog-stub"><slot /><slot name="footer" /></div>' } } },
  })
}

describe('GroupManagementView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    route.query = {}
    store.groups = [{ id: 1, name: 'Gruppe 1' }]
    store.members = [member(10, 'Mila', 1), member(11, 'Jonas', null)]
    store.fetchGroups.mockResolvedValue(store.groups)
    store.fetchAllMembers.mockResolvedValue(store.members)
  })

  it('shows missing rights instead of an empty board', async () => {
    store.fetchAllMembers.mockRejectedValueOnce({ response: { status: 403 } })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Berechtigung für Gruppen')
    expect(wrapper.find('.group-board').exists()).toBe(false)
    wrapper.unmount()
  })

  it('has one main action, named group actions and text counts', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.get('.overview-header__actions').findAll('button').map((b) => b.text())).toEqual(['Gruppe anlegen'])
    expect(wrapper.get('.overview-header__subtitle').text()).toBe('2 Mitglieder · 1 Gruppe')
    expect(wrapper.find('[aria-label="Gruppe Gruppe 1 umbenennen"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Gruppe Gruppe 1 löschen"]').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Mila Muster: Gruppe wechseln"]').exists()).toBe(true)
    expect(wrapper.findAll('.column-count').map((c) => c.attributes('aria-label'))).toEqual(['1 Mitglied', '1 Mitglied'])
    wrapper.unmount()
  })

  it('filters from the URL search', async () => {
    route.query = { search: 'jon' }
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Jonas Muster')
    expect(wrapper.text()).not.toContain('Mila Muster')
    wrapper.unmount()
  })

  it('keeps rename and create errors at the field', async () => {
    store.createGroup.mockRejectedValue({ response: { status: 400, data: { name: ['Name bereits vergeben.'] } } })
    const wrapper = render()
    await flushPromises()

    await wrapper.get('[aria-label="Gruppe Gruppe 1 umbenennen"]').trigger('click')
    const rename = wrapper.get('[aria-label="Neuer Name für Gruppe 1"]')
    await rename.setValue('   ')
    await rename.trigger('keyup', { key: 'Enter' })
    expect(store.updateGroup).not.toHaveBeenCalled()
    expect(rename.attributes('aria-invalid')).toBe('true')
    expect(wrapper.get('#rename-error-1').text()).toBe('Bitte einen Namen eingeben.')

    await wrapper.get('#new-group-name').setValue('Gruppe 1')
    await wrapper.findAll('.dialog-stub button').find((b) => b.text() === 'Gruppe anlegen')!.trigger('click')
    await flushPromises()
    expect(wrapper.get('#new-group-error').text()).toBe('Name bereits vergeben.')
    expect(wrapper.get('#new-group-name').attributes('aria-describedby')).toBe('new-group-error')
    wrapper.unmount()
  })
})
