import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import MemberDetailView from '../MemberDetailView.vue'

const { auth, membersApi, qualificationsApi, servicebookApi } = vi.hoisted(() => ({
  auth: { canAccessModule: vi.fn((_perm: string) => true), hasPerm: vi.fn((_perm: string) => false) },
  membersApi: { get: vi.fn(), getParents: vi.fn(), getEvents: vi.fn(), delete: vi.fn(), deleteWithStrategy: vi.fn() },
  qualificationsApi: { list: vi.fn() },
  servicebookApi: { attendance: { getByMember: vi.fn() } },
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('@/api/members', () => ({ membersApi, parentsApi: { delete: vi.fn() } }))
vi.mock('@/api/qualifications', () => ({ qualificationsApi }))
vi.mock('@/api/servicebook', () => ({ servicebookApi }))
vi.mock('@/composables/usePrivateMedia', () => ({ usePrivateMedia: () => ({ value: undefined }) }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: '5' } }), useRouter: () => ({ push: vi.fn() }) }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: vi.fn() }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))

globalThis.ResizeObserver ??= class { observe() {} unobserve() {} disconnect() {} } as unknown as typeof ResizeObserver

const member = {
  id: 5, name: 'Lena', lastname: 'Weber', full_name: 'Lena Weber', birthday: '2014-03-14', age: 12,
  email: '', street: 'Lindenweg 4', zip_code: '12345', city: 'Musterstadt', phone: '', mobile: '',
  notes: 'Fiktiver Hinweis', joined: '2024-09-01', identityCardNumber: '', canSwimm: true, gender: '',
  status: { id: 1, name: 'Aktiv', color: '#16a34a' }, group: { id: 2, name: 'Gruppe B' },
  storage_location: null, avatar: null, avatar_url: null, has_alert: false, department_ids: [1],
}
const parents = [
  { id: 7, name: 'Daniel', lastname: 'Weber', full_name: 'Daniel Weber', phone: '', mobile: '', email: '', children: [5] },
  { id: 8, name: 'Katrin', lastname: 'Weber', full_name: 'Katrin Weber', phone: '', mobile: '0171 1234567', email: 'k@example.org', children: [5] },
]

function render() {
  return mount(MemberDetailView, {
    global: {
      plugins: [PrimeVue],
      stubs: {
        RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
        QualificationsManager: true, SpecialTasksManager: true, EventsManager: true,
        AttendanceTab: true, MemberEquipmentTab: true, AttachmentsManager: true, MemberDeletionDialog: true, AccountLinkCard: true,
      },
    },
  })
}

describe('MemberDetailView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    auth.canAccessModule.mockImplementation(() => true)
    membersApi.get.mockResolvedValue({ data: member })
    membersApi.getParents.mockResolvedValue({ data: parents })
    membersApi.getEvents.mockResolvedValue({ data: [] })
    qualificationsApi.list.mockResolvedValue({ data: { results: [
      { id: 1, type_name: 'Erste-Hilfe-Grundkurs', date_acquired: '2023-10-19', date_expires: '2026-10-19', is_expired: false, expires_soon: true },
    ] } })
    servicebookApi.attendance.getByMember.mockResolvedValue({ data: {
      attendances: [
        { id: 2, service_date: '2026-09-30', state: 'A', state_display: 'Anwesend' },
        { id: 1, service_date: '2026-09-23', state: 'F', state_display: 'Fehlend' },
      ],
      summary: { present: 1, excused: 0, absent: 1, total: 2 },
    } })
  })

  it('calls the first reachable contact and offers to add missing numbers', async () => {
    const wrapper = render()
    await flushPromises()
    const call = wrapper.get('a.contact__action--call')
    expect(call.attributes('href')).toBe('tel:0171 1234567')
    expect(call.attributes('aria-label')).toBe('Katrin Weber anrufen')
    expect(wrapper.get('[aria-label="Telefonnummer für Daniel Weber ergänzen"]').attributes('href')).toBe('/parents/7/edit')
    expect(wrapper.get('.quick-action--primary').text()).toContain('Katrin anrufen')
  })

  it('keeps notes hidden until requested', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).not.toContain('Fiktiver Hinweis')
    const toggle = wrapper.get('button[aria-controls="member-notes"]')
    expect(toggle.attributes('aria-expanded')).toBe('false')
    await toggle.trigger('click')
    expect(wrapper.text()).toContain('Fiktiver Hinweis')
    expect(toggle.attributes('aria-expanded')).toBe('true')
  })

  it('summarises attendance oldest first and flags expiring qualifications', async () => {
    const wrapper = render()
    await flushPromises()
    const strip = wrapper.get('.attendance-strip')
    expect(strip.attributes('aria-label')).toBe('Letzte 2 Dienste: 1 anwesend · 0 entschuldigt · 1 gefehlt')
    expect(strip.findAll('li').map(li => li.classes())).toEqual([
      expect.arrayContaining(['attendance-mark--F']),
      expect.arrayContaining(['attendance-mark--A']),
    ])
    expect(wrapper.text()).toContain('Läuft am 19.10.2026 ab')
    expect(wrapper.get('.facts').text()).toContain('50 %')
  })

  it('shows a failed source on its own and skips sources without permission', async () => {
    auth.canAccessModule.mockImplementation((perm: string) => perm !== 'view_service')
    qualificationsApi.list.mockRejectedValueOnce({ response: { status: 500 } })
    const wrapper = render()
    await flushPromises()
    expect(servicebookApi.attendance.getByMember).not.toHaveBeenCalled()
    expect(wrapper.find('#attendance-heading').exists()).toBe(false)
    const failed = wrapper.get('[aria-labelledby="qualifications-heading"] [role="alert"]')
    expect(failed.text()).toContain('Laden fehlgeschlagen')
    expect(wrapper.text()).toContain('Noch keine Einträge.')
    expect(wrapper.text()).toContain('Kann schwimmen')
  })
})
