import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ServiceAttendanceView from '../ServiceAttendanceView.vue'

const m = vi.hoisted(() => ({
  get: vi.fn(),
  route: { name: 'service-detail', params: { id: '11' } as Record<string, string>, query: {} as Record<string, string> },
  replace: vi.fn(),
  user: null as unknown,
  store: { currentService: null, fetchService: vi.fn(), updateService: vi.fn() },
  registrations: { registrations: null, registrationsLoading: false, registrationsError: null, reset: vi.fn(), fetchRegistrations: vi.fn() },
}))
vi.mock('@/api/servicebook', () => ({ servicesApi: { get: m.get } }))
vi.mock('vue-router', () => ({ useRoute: () => m.route, useRouter: () => ({ push: vi.fn(), replace: m.replace }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))
vi.mock('@/stores/servicebook', () => ({ useServicebookStore: () => m.store }))
vi.mock('@/stores/serviceRegistrations', () => ({ useServiceRegistrationsStore: () => m.registrations }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ get user() { return m.user } }) }))
vi.mock('@/components/servicebook/molecules/DeleteServiceButton.vue', () => ({ default: { template: '<div />' } }))

const service = {
  id: 11, start: '2026-10-16T18:00:00+02:00', end: '2026-10-16T20:00:00+02:00', topic: 'Stationsausbildung', place: 'Übungshof',
  description: 'Saugleitung kuppeln', events: '', department: 1, operations_manager: [{ id: 1, username: 'jk', full_name: 'Jan Keller', email: '' }],
}

function render() {
  return mount(ServiceAttendanceView, {
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' },
        ServiceForm: { name: 'ServiceForm', props: ['submitLabel'], template: '<div class="form-stub">{{ submitLabel }}</div>' },
        AttendanceManager: { template: '<div class="attendance-stub" />' },
        ServiceRegistrations: true,
        ServiceEventsNote: { template: '<div class="events-stub" />' },
        ExcusedTakeoverSheet: true,
      },
    },
  })
}

describe('ServiceAttendanceView (one service page, FIX-05)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    m.get.mockResolvedValue({ data: service })
    m.route.name = 'service-detail'
    m.route.query = {}
    m.user = { is_superuser: false, permissions: [], department_roles: [{ department_id: 1, permissions: ['servicebook.change_service'] }] }
  })

  it('opens on the service data with the edit form for editors', async () => {
    const wrapper = render()
    await flushPromises()
    const tabs = wrapper.findAll('[role="tab"]').map(t => t.text())
    expect(tabs).toEqual(['Dienstdaten', 'Meldungen', 'Anwesenheit', 'Betreuende'])
    expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toBe('Dienstdaten')
    expect(wrapper.get('.form-stub').text()).toBe('Änderungen speichern')
    expect(m.store.fetchService).toHaveBeenCalledWith(11)
  })

  it('shows description and leaders read-only without the edit right', async () => {
    m.user = { is_superuser: false, permissions: [], department_roles: [{ department_id: 1, permissions: ['servicebook.view_service'] }] }
    const wrapper = render()
    await flushPromises()
    expect(wrapper.find('.form-stub').exists()).toBe(false)
    expect(wrapper.get('.service-facts').text()).toContain('Saugleitung kuppeln')
    expect(wrapper.get('.service-facts').text()).toContain('Jan Keller')
    expect(wrapper.findAll('[role="tab"]').map(t => t.text())).toContain('Vorkommnisse')
  })

  it('keeps the attendance route on "Anwesenheit"', async () => {
    m.route.name = 'service-attendance'
    const wrapper = render()
    await flushPromises()
    expect(wrapper.get('[role="tab"][aria-selected="true"]').text()).toBe('Anwesenheit')
    expect(wrapper.find('.attendance-stub').exists()).toBe(true)
  })
})
