import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import { reactive } from 'vue'
import ListDetailView from '../ListDetailView.vue'

const { store, confirmRequire, toastAdd, push } = vi.hoisted(() => ({
  store: {} as Record<string, unknown>,
  confirmRequire: vi.fn(),
  toastAdd: vi.fn(),
  push: vi.fn(),
}))
vi.mock('@/stores/lists', () => ({ useMemberListsStore: () => store }))
vi.mock('@/stores/members', () => ({ useMembersStore: () => ({ members: [], fetchMembers: vi.fn() }) }))
vi.mock('@/stores/groups', () => ({ useGroupsStore: () => ({ groups: [], fetchGroups: vi.fn() }) }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: null }) }))
vi.mock('@/composables/useListPdf', () => ({ useListPdf: () => ({ generateChecklist: vi.fn() }) }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: '3' } }), useRouter: () => ({ push }) }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: confirmRequire }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

function entry(id: number, name: string, checked: boolean) {
  return {
    id, checked, checked_at: checked ? '2026-10-06T16:41:00Z' : null, notes: '', added_at: '',
    member: { id, full_name: name, name: name.split(' ')[0], lastname: name.split(' ')[1], group: { id: 1, name: 'Gruppe A' } },
  }
}

function resetStore() {
  Object.assign(store, reactive({
    loading: false,
    saving: false,
    currentList: {
      id: 3, name: 'Einverständnis Ausflug', description: '', color: '#0e7490', department: 1, member_count: 3, checked_count: 1,
      entries: [entry(1, 'Jonas Becker', false), entry(2, 'Lena Weber', true), entry(3, 'Tim Hoffmann', false)],
    },
    fetchList: vi.fn(),
    toggleCheck: vi.fn(),
    checkAll: vi.fn(),
    uncheckAll: vi.fn(),
    updateEntryNotes: vi.fn(),
    removeMember: vi.fn(),
  }))
}

function render() {
  return mount(ListDetailView, {
    global: {
      plugins: [PrimeVue],
      stubs: { RouterLink: { props: ['to'], template: '<a href="#"><slot /></a>' }, AttachmentsSection: true, MemberExportDialog: true },
    },
  })
}

describe('ListDetailView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resetStore()
  })

  it('checks entries with accessible toggles and shows progress', async () => {
    const wrapper = render()
    await flushPromises()
    const toggles = wrapper.findAll('[role="checkbox"]')
    expect(toggles.map(t => t.attributes('aria-checked'))).toEqual(['false', 'true', 'false'])
    expect(toggles[0]!.element.tagName).toBe('BUTTON')
    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBe('1')
    expect(wrapper.text()).toContain('1 von 3 erledigt')
    expect(wrapper.text()).toContain('Offen (2)')
    await toggles[0]!.trigger('click')
    expect(store.toggleCheck).toHaveBeenCalledWith(3, 1)
  })

  it('shows saving and a failed save instead of failing silently', async () => {
    let reject!: (e: unknown) => void
    ;(store.toggleCheck as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise((_, r) => { reject = r }))
    const wrapper = render()
    await flushPromises()
    await wrapper.findAll('[role="checkbox"]')[0]!.trigger('click')
    expect(wrapper.get('.save-state').text()).toBe('Speichert …')
    reject(new Error('offline'))
    await flushPromises()
    expect(wrapper.get('.save-state').text()).toBe('Nicht gespeichert')
    expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error' }))
  })

  it('keeps adding, notes and removal out of the checking mode', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.find('[aria-label="Jonas Becker aus der Liste entfernen"]').exists()).toBe(false)
    expect(wrapper.find('#add-panel-title').exists()).toBe(false)
    await wrapper.get('button[aria-pressed="false"].p-button').trigger('click')
    expect(wrapper.find('[aria-label="Jonas Becker aus der Liste entfernen"]').exists()).toBe(true)
    expect(wrapper.find('#add-panel-title').exists()).toBe(true)
  })

  it('filters open entries and reminds only open members', async () => {
    const wrapper = render()
    await flushPromises()
    await wrapper.findAll('.segmented button')[0]!.trigger('click')
    expect(wrapper.findAll('[role="checkbox"]').length).toBe(2)
    await wrapper.findAll('button').find(b => b.text().includes('Offene erinnern'))!.trigger('click')
    expect(push).toHaveBeenCalledWith(expect.objectContaining({ state: expect.objectContaining({ preselectedMemberIds: [1, 3] }) }))
  })
})
