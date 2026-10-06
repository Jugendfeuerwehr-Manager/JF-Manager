import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
import AttendanceManager from '../organisms/AttendanceManager.vue'

const { servicesApi, toastAdd } = vi.hoisted(() => ({
  servicesApi: { getAttendanceBoard: vi.fn(), updateAttendanceBoard: vi.fn(), getStaffStatistics: vi.fn() },
  toastAdd: vi.fn(),
}))
vi.mock('@/api/servicebook', () => ({ servicesApi }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

const global = {
  plugins: [PrimeVue],
  directives: { tooltip: Tooltip },
  stubs: { RouterLink: { props: ['to'], template: '<a :data-to="JSON.stringify(to)"><slot /></a>' } },
}

function board() {
  return {
    members: [
      { id: 1, full_name: 'Lena Weber', state: null },
      { id: 2, full_name: 'Tim Hoffmann', state: 'A' },
    ],
    staff: [{ id: 9, full_name: 'Alex Muster', state: null }],
  }
}

describe('AttendanceManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    servicesApi.getAttendanceBoard.mockImplementation(async () => ({ data: board() }))
  })
  afterEach(() => vi.useRealTimers())

  it('shows open people first with named, labelled status buttons', async () => {
    const wrapper = mount(AttendanceManager, { props: { serviceId: 5 }, global })
    await flushPromises()
    expect(wrapper.text()).toContain('1 von 2 erfasst')
    const rows = wrapper.findAll('.person')
    expect(rows.length).toBe(1)
    const group = rows[0]!.get('[role="group"]')
    expect(group.attributes('aria-label')).toBe('Anwesenheit von Lena Weber')
    expect(group.findAll('button').map(b => b.text())).toEqual(['Anwesend', 'Entschuldigt', 'Fehlt'])
    expect(group.findAll('button').every(b => b.attributes('aria-pressed') === 'false')).toBe(true)
    wrapper.unmount()
  })

  it('keeps a just-marked person visible to correct a mis-tap and reports the save', async () => {
    let resolveSave!: (value: unknown) => void
    servicesApi.updateAttendanceBoard.mockImplementation(() => new Promise((resolve) => { resolveSave = resolve }))
    servicesApi.getAttendanceBoard
      .mockResolvedValueOnce({ data: board() })
      .mockResolvedValue({ data: { ...board(), members: [{ id: 1, full_name: 'Lena Weber', state: 'A' }, board().members[1]] } })
    const wrapper = mount(AttendanceManager, { props: { serviceId: 5 }, global })
    await flushPromises()
    await wrapper.get('.person [role="group"] button').trigger('click')
    expect(wrapper.get('.save-state').text()).toBe('Speichert …')
    resolveSave({ data: { state: 'A' } })
    await flushPromises()
    expect(servicesApi.updateAttendanceBoard).toHaveBeenCalledWith(5, { kind: 'member', person_id: 1, state: 'A', expected_state: null })
    expect(wrapper.get('.save-state').text()).toBe('Gespeichert')
    expect(wrapper.findAll('.person').length).toBe(1)
    expect(wrapper.get('.person button[aria-pressed="true"]').text()).toBe('Anwesend')
    await wrapper.findAll('.segmented button')[0]!.trigger('click')
    expect(wrapper.findAll('.person').length).toBe(0)
    expect(wrapper.text()).toContain('Alle Anwesenheiten sind erfasst.')
    wrapper.unmount()
  })

  it('rolls back and says so when saving fails', async () => {
    servicesApi.updateAttendanceBoard.mockRejectedValue({ response: { status: 409 } })
    const wrapper = mount(AttendanceManager, { props: { serviceId: 5 }, global })
    await flushPromises()
    await wrapper.get('.person [role="group"] button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.save-state').text()).toBe('Nicht gespeichert')
    expect(wrapper.get('.person [role="group"] button').attributes('aria-pressed')).toBe('false')
    expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error' }))
    wrapper.unmount()
  })
})
