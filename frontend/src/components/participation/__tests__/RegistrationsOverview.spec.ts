import PrimeVue from 'primevue/config'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import RegistrationsOverview from '../RegistrationsOverview.vue'
import RulePreview from '../RulePreview.vue'
import { participationApi } from '@/api/participation'

vi.mock('@/api/participation', () => ({
  participationApi: { config: vi.fn(), saveConfig: vi.fn(), registrations: vi.fn(), setRegistration: vi.fn(), validate: vi.fn(), preview: vi.fn() },
}))
const api = vi.mocked(participationApi)

const row = (id: number, name: string, state: string, extra = {}) => ({
  member_id: id, name, lastname: 'Muster', group_id: 1, in_target: true, state, waitlist_position: null,
  eligibility: { ok: true, reasons: [] }, registration: null, ...extra,
})
const overview = (mode = 'opt_in') => ({
  session: { id: 7, title: 'Übung', date: '2030-01-01', start_time: '18:00:00', status: 'published' }, mode, revision: 1,
  deadlines: { registration_opens_at: null, registration_closes_at: '2029-12-30T18:00:00Z', cancellation_closes_at: '2030-01-01T16:00:00Z' },
  counts: { registered: 1, waitlisted: 1, applied: 0, assigned: 0, not_selected: 0, cancelled: 1, expected: 0, no_response: 1, conflicts: 1, late: 1, seated: 1, max_participants: 1, min_participants: null, free: 0 },
  truncated: false,
  members: [
    row(1, 'Anna', 'registered', { registration: { version: 2, reason_category: '', reason_note: null, source: 'staff', late: true, conflict: true, conflict_reasons: ['Qualifikation abgelaufen'], state_changed_at: '' } }),
    row(2, 'Ben', 'waitlisted', { waitlist_position: 1 }),
    row(3, 'Cem', 'cancelled', { registration: { version: 1, reason_category: 'krankheit', reason_note: null, source: 'portal_member', late: false, conflict: false, conflict_reasons: [], state_changed_at: '' } }),
    row(4, 'Dora', 'no_response', { eligibility: { ok: false, reasons: ['Alter fehlt'] } }),
  ],
})

describe('RegistrationsOverview', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.resetAllMocks() })

  it('lists people with state text, reason and hints', async () => {
    api.registrations.mockResolvedValue({ data: overview() } as never)
    const wrapper = mount(RegistrationsOverview, { props: { sessionId: 7, canManage: true }, global: { plugins: [PrimeVue] } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('Warteliste, Platz 1')
    expect(text).toContain('Krankheit')
    expect(text).toContain('Nach Frist erfasst')
    expect(text).toContain('Voraussetzung nicht mehr erfüllt: 1')
    expect(text).toContain('Voraussetzung nicht mehr erfüllt: Qualifikation abgelaufen')
    expect(text).toContain('Voraussetzungen nicht erfüllt: Alter fehlt')
    expect(text).toContain('Plätze: 1 von 1 belegt, 0 frei')
  })

  it('registers a person directly and cancels via the reason dialog', async () => {
    api.registrations.mockResolvedValue({ data: overview() } as never)
    api.setRegistration.mockResolvedValue({ data: {} } as never)
    const wrapper = mount(RegistrationsOverview, { props: { sessionId: 7, canManage: true }, global: { plugins: [PrimeVue], stubs: { Dialog: { template: '<div><slot /><slot name="footer" /></div>' } } } })
    await flushPromises()
    await wrapper.find('button[aria-label="Dora Muster anmelden"]').trigger('click')
    await flushPromises()
    expect(api.setRegistration).toHaveBeenCalledWith(7, 4, expect.objectContaining({ target: 'registered' }))
    await wrapper.find('button[aria-label="Anna Muster abmelden"]').trigger('click')
    await wrapper.find('#reg-reason').setValue('urlaub')
    await wrapper.findAll('button').filter(b => b.text() === 'Abmelden').at(-1)!.trigger('click')
    await flushPromises()
    expect(api.setRegistration).toHaveBeenLastCalledWith(7, 1, expect.objectContaining({ target: 'cancelled', reason_category: 'urlaub', version: 2 }))
  })

  it('offers no "anmelden" in assignment mode and no actions without permission', async () => {
    api.registrations.mockResolvedValue({ data: overview('assignment') } as never)
    const wrapper = mount(RegistrationsOverview, { props: { sessionId: 7, canManage: true }, global: { plugins: [PrimeVue] } })
    await flushPromises()
    expect(wrapper.find('button[aria-label$="anmelden"]').exists()).toBe(false)
    const viewer = mount(RegistrationsOverview, { props: { sessionId: 7, canManage: false }, global: { plugins: [PrimeVue] } })
    await flushPromises()
    expect(viewer.find('button[aria-label$="abmelden"]').exists()).toBe(false)
  })
})

describe('RulePreview', () => {
  const base = { summary: '', total: 41, eligible: 0, excluded: [{ member_id: 1, name: 'Anna Muster', reasons: ['Qualifikation ‚Maschinist‘ fehlt'] }], errors: {}, audience_notice: null }
  it('hints at zero matches and lists exclusions with reasons', () => {
    const wrapper = mount(RulePreview, { props: { preview: base } })
    expect(wrapper.text()).toContain('Niemand erfüllt diese Voraussetzungen')
    expect(wrapper.text()).toContain('Ausgeschlossen (1)')
    expect(wrapper.text()).toContain('Qualifikation ‚Maschinist‘ fehlt')
  })
  it('names the higher qualification that fulfils a requirement', () => {
    const substituted = [{ member_id: 2, name: 'Ben Beispiel', notes: ['Qualifikation ‚Truppmann‘ erfüllt durch ‚Truppführer‘'] }]
    const wrapper = mount(RulePreview, { props: { preview: { ...base, eligible: 1, substituted } } })
    expect(wrapper.text()).toContain('Erfüllt durch höhere Qualifikation (1)')
    expect(wrapper.text()).toContain('erfüllt durch ‚Truppführer‘')
  })
  it('waits for valid conditions while rule errors exist', () => {
    const wrapper = mount(RulePreview, { props: { preview: base, errors: { 'rules[0].max': 'x' } } })
    expect(wrapper.text()).toContain('sobald alle Bedingungen gültig sind')
    expect(wrapper.text()).not.toContain('Ausgeschlossen')
  })
})
