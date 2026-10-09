import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ServiceRegistrations from '../organisms/ServiceRegistrations.vue'
import AttendanceManager from '../organisms/AttendanceManager.vue'
import ExcusedTakeoverSheet from '../organisms/ExcusedTakeoverSheet.vue'
import type { RegistrationPerson, ServiceRegistrations as Data } from '@/types/servicebook'

const { servicesApi, toastAdd } = vi.hoisted(() => ({
  servicesApi: { getAttendanceBoard: vi.fn(), updateAttendanceBoard: vi.fn(), applyExcused: vi.fn() },
  toastAdd: vi.fn(),
}))
vi.mock('@/api/servicebook', () => ({ servicesApi }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

const global = {
  plugins: [PrimeVue],
  stubs: { RouterLink: { props: ['to'], template: '<a><slot /></a>' } },
}

const person = (id: number, name: string, extra: Partial<RegistrationPerson> = {}): RegistrationPerson => ({
  member_id: id, name, group: 'Gruppe 2', state: 'expected', waitlist_position: null, reason_category: null,
  reason_note: null, source: null, at: null, late: false, conflict: false, in_target: true, attendance: null, ...extra,
})

function data(): Data {
  return {
    session: { id: 4, mode: 'opt_out', max_participants: null, deadlines: { registration_closes_at: null, cancellation_closes_at: null } },
    counts: { expected: 3, registered: 1, cancelled: 2, waitlisted: 1, applied: 0, assigned: 0, no_response: 1, conflicts: 0, recorded: 0, guests: 1 },
    people: [
      person(1, 'Mia Becker', { state: 'cancelled', reason_category: 'urlaub', reason_note: 'Familienreise', source: 'portal_parent' }),
      person(2, 'Paul Neumann', { state: 'cancelled', reason_category: 'krankheit' }),
      person(3, 'Lina Hartmann', { state: 'registered', in_target: false }),
      person(4, 'Tim Wolf', { state: 'waitlisted', waitlist_position: 2 }),
      person(5, 'Ella Schulz', { state: 'no_response' }),
      person(6, 'Jan Roth', { state: 'expected' }),
    ],
  }
}

describe('ServiceRegistrations', () => {
  it('groups people by state, shows the reason category and reveals the note only on tap', async () => {
    const wrapper = mount(ServiceRegistrations, { props: { data: data() }, global })
    expect(wrapper.findAll('h3').map((h) => h.text())).toEqual(['Abgemeldet (2)', 'Angemeldet (1)', 'Warteliste (1)', 'Erwartet ohne Meldung (1)', 'Keine Rückmeldung (1)'])
    expect(wrapper.text()).toContain('Urlaub')
    expect(wrapper.text()).toContain('Krankheit')
    expect(wrapper.text()).toContain('Platz 2')
    expect(wrapper.text()).not.toContain('Familienreise')
    const toggles = wrapper.findAll('.reg-row__toggle')
    expect(toggles).toHaveLength(1)
    expect(toggles[0]!.attributes('aria-expanded')).toBe('false')
    await toggles[0]!.trigger('click')
    expect(wrapper.text()).toContain('Familienreise')
    expect(toggles[0]!.attributes('aria-expanded')).toBe('true')
  })

  it('explains a service without registration', () => {
    const wrapper = mount(ServiceRegistrations, { props: { data: { ...data(), session: null } }, global })
    expect(wrapper.text()).toContain('Keine Anmeldung für diesen Dienst')
  })
})

describe('AttendanceManager with registrations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    servicesApi.getAttendanceBoard.mockResolvedValue({
      data: {
        members: [
          { id: 1, full_name: 'Mia Becker', state: null },
          { id: 2, full_name: 'Paul Neumann', state: 'E' },
          { id: 5, full_name: 'Ella Schulz', state: null },
        ],
        staff: [],
      },
    })
  })

  it('shows the registration status as text, a guest row, chips and the takeover entry', async () => {
    const wrapper = mount(AttendanceManager, { props: { serviceId: 5, fixedKind: 'member', registrations: data() }, global })
    await flushPromises()
    expect(wrapper.findAll('.chip').map((c) => c.text().replace(/\s+/g, ' '))).toEqual(['Alle 4', 'Offen 3', 'Abgemeldet 2', 'Gäste 1'])
    const rows = wrapper.findAll('.person')
    expect(rows.map((r) => r.get('.person__name').text())).toEqual(['Mia Becker', 'Ella Schulz', 'Lina Hartmann'])
    expect(rows[0]!.text()).toContain('abgemeldet · Urlaub')
    expect(rows[0]!.classes()).toContain('person--suggest')
    expect(rows[0]!.get('.attendance-option--suggest').text()).toContain('Vorschlag')
    expect(rows[2]!.text()).toContain('Gast')
    expect(wrapper.get('.takeover').text()).toContain('1 Abmeldung als entschuldigt übernehmen')

    await wrapper.findAll('.chip')[3]!.trigger('click')
    expect(wrapper.findAll('.person').map((r) => r.get('.person__name').text())).toEqual(['Lina Hartmann'])
    await wrapper.get('.takeover').trigger('click')
    expect(wrapper.emitted('takeover')).toHaveLength(1)
  })

  it('saves attendance for a guest through the existing board API', async () => {
    servicesApi.updateAttendanceBoard.mockResolvedValue({ data: { state: 'A' } })
    const wrapper = mount(AttendanceManager, { props: { serviceId: 5, fixedKind: 'member', registrations: data() }, global })
    await flushPromises()
    await wrapper.findAll('.chip')[3]!.trigger('click')
    await wrapper.get('.person button').trigger('click')
    await flushPromises()
    expect(servicesApi.updateAttendanceBoard).toHaveBeenCalledWith(5, { kind: 'member', person_id: 3, state: 'A', expected_state: null })
  })
})

describe('ExcusedTakeoverSheet', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('previews, preselects only people without attendance and applies the chosen ids', async () => {
    servicesApi.applyExcused
      .mockResolvedValueOnce({ data: { apply: [{ member_id: 1, name: 'Mia Becker' }, { member_id: 2, name: 'Paul Neumann' }], skipped: [{ member_id: 9, name: 'Noah Fischer', reason: 'has_attendance' }], applied: 0 } })
      .mockResolvedValueOnce({ data: { apply: [], skipped: [], applied: 1 } })
    const wrapper = mount(ExcusedTakeoverSheet, { props: { serviceId: 5 }, global: { ...global, stubs: {} }, attachTo: document.body })
    await flushPromises()
    expect(servicesApi.applyExcused).toHaveBeenNthCalledWith(1, 5, { dry_run: true })
    const dialog = wrapper.get('[role="dialog"]')
    expect(dialog.attributes('aria-modal')).toBe('true')
    expect(wrapper.text()).toContain('Noah Fischer')
    expect(wrapper.text()).toContain('bleibt unverändert')
    const boxes = wrapper.findAll('input[type="checkbox"]')
    expect(boxes.every((b) => (b.element as HTMLInputElement).checked)).toBe(true)
    expect(wrapper.get('.btn--primary').text()).toBe('2 übernehmen')
    await boxes[1]!.setValue(false)
    expect(wrapper.get('.btn--primary').text()).toBe('1 übernehmen')
    await wrapper.get('.btn--primary').trigger('click')
    await flushPromises()
    expect(servicesApi.applyExcused).toHaveBeenNthCalledWith(2, 5, { dry_run: false, member_ids: [1] })
    expect(wrapper.text()).toContain('1 Person als entschuldigt übernommen')
    expect(wrapper.emitted('applied')?.[0]).toEqual([1])
    wrapper.unmount()
  })
})
