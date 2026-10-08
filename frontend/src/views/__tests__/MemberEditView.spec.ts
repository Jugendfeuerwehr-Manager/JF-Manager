import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import MemberEditView from '../MemberEditView.vue'

const { auth, members, departments, push } = vi.hoisted(() => ({
  auth: { isOrgWide: false },
  members: {
    loading: false, statuses: [{ id: 1, name: 'Aktiv', color: '#16a34a' }, { id: 2, name: 'Probezeit', color: '#0284c7' }], groups: [],
    statusOptions: [{ label: 'Aktiv', value: 1 }, { label: 'Probezeit', value: 2 }], groupOptions: [],
    fetchStatuses: vi.fn(), fetchGroups: vi.fn(), fetchMemberById: vi.fn(), updateMember: vi.fn(), createMember: vi.fn(),
  },
  departments: { loading: false, departments: [{ id: 1, name: 'Musterstadt-Nord', code: 'NORD' }], fetchDepartments: vi.fn() },
  push: vi.fn(),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('@/stores/members', () => ({ useMembersStore: () => members }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => departments }))
vi.mock('@/composables/usePrivateMedia', () => ({ usePrivateMedia: () => ({ value: undefined }) }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: '5' } }), useRouter: () => ({ push }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))

window.matchMedia ??= ((query: string) => ({ matches: false, media: query, addEventListener() {}, removeEventListener() {} })) as unknown as typeof window.matchMedia
globalThis.ResizeObserver ??= class { observe() {} unobserve() {} disconnect() {} } as unknown as typeof ResizeObserver
window.HTMLElement.prototype.scrollIntoView ??= function () {}

const member = {
  id: 5, name: 'Lena', lastname: 'Weber', full_name: 'Lena Weber', birthday: '2014-03-14', age: 12, email: '', street: '',
  zip_code: '', city: '', phone: '', mobile: '', notes: '', joined: null, identityCardNumber: '', canSwimm: true, gender: '',
  status: { id: 1, name: 'Aktiv', color: '#16a34a' }, group: null, storage_location: null, avatar: null, avatar_url: null,
  has_alert: false, department_ids: [1],
  parents: [{ id: 8, name: 'Daniel', lastname: 'Weber', full_name: 'Daniel Weber', phone: '', mobile: '', email: '', children: [5] }],
}

function render() {
  return mount(MemberEditView, {
    attachTo: document.body,
    global: { plugins: [PrimeVue], stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } },
  })
}

describe('MemberEditView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    auth.isOrgWide = false
    members.fetchMemberById.mockResolvedValue(member)
    members.updateMember.mockResolvedValue(member)
  })

  it('locks departments for department-scoped editors and leaves them out of the request', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('Abteilungen ändert die Organisationsverwaltung.')
    expect(wrapper.text()).toContain('NORD · Musterstadt-Nord')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    const body = members.updateMember.mock.calls[0]![1] as FormData
    expect(body.has('departments')).toBe(false)
    expect(push).toHaveBeenCalledWith('/members/5')
    wrapper.unmount()
  })

  it('flags unsaved changes and selects the status as a choice', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).not.toContain('Ungespeicherte Änderungen')
    await wrapper.get('input[type="radio"][value="2"]').setValue(true)
    expect(wrapper.text()).toContain('Ungespeicherte Änderungen')
    expect(wrapper.get('.choice--selected').text()).toBe('Probezeit')
    wrapper.unmount()
  })

  it('counts errors per section, focuses the first invalid field and does not save', async () => {
    const wrapper = render()
    await flushPromises()
    await wrapper.get('#name').setValue('')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(members.updateMember).not.toHaveBeenCalled()
    expect(wrapper.get('#name').attributes('aria-invalid')).toBe('true')
    expect(wrapper.get('#name').attributes('aria-describedby')).toBe('name-error')
    expect(wrapper.get('.section-nav__errors').attributes('aria-label')).toBe('1 Fehler')
    expect(wrapper.get('.action-bar__status').text()).toContain('1 Feld braucht deine Aufmerksamkeit')
    expect(document.activeElement?.id).toBe('name')
    wrapper.unmount()
  })

  it('shows linked guardians with a missing emergency number', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.get('.parent').text()).toContain('Notfallnummer fehlt')
    wrapper.unmount()
  })
})
