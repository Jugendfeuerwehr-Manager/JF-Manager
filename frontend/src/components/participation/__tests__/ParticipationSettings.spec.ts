import PrimeVue from 'primevue/config'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import ParticipationSettings from '../ParticipationSettings.vue'
import { participationApi } from '@/api/participation'

vi.mock('@/api/participation', () => ({
  participationApi: { config: vi.fn(), saveConfig: vi.fn(), registrations: vi.fn(), setRegistration: vi.fn(), validate: vi.fn(), preview: vi.fn() },
}))
vi.mock('@/composables/useRuleOptions', () => ({
  useRuleOptions: () => ({
    options: ref({ qualification: [], special_task: [], gender: [], group: [], status: [], department: [] }),
    loading: ref(false), error: ref(null), load: vi.fn(),
  }),
}))
const api = vi.mocked(participationApi)

const config = (over = {}) => ({
  session: 7, revision: 1, mode: 'opt_in', portal_visible: true, public_note: '', registration_opens_at: null,
  registration_closes_at: null, cancellation_closes_at: null, max_participants: 12, min_participants: 4, waitlist_mode: 'auto',
  eligibility: {}, effective: { start: '2030-01-01T18:00:00Z', registration_opens_at: null, registration_closes_at: '2029-12-30T18:00:00Z', cancellation_closes_at: '2030-01-01T16:00:00Z' },
  defaults: { mode: 'opt_out', registration_offset_h: 48, cancellation_offset_h: 2, waitlist_mode: 'auto' },
  eligibility_summary: null, audience_notice: null, ...over,
})

async function mountPanel(over = {}) {
  api.config.mockResolvedValue({ data: config(over) } as never)
  api.preview.mockResolvedValue({ data: { summary: 'Keine besonderen Voraussetzungen', total: 41, eligible: 18, excluded: [], errors: {}, audience_notice: null } } as never)
  const wrapper = mount(ParticipationSettings, { props: { sessionId: 7 }, global: { plugins: [PrimeVue] } })
  await flushPromises()
  return wrapper
}

describe('ParticipationSettings', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.resetAllMocks() })

  it('edits positions: derived and locked maximum, staffing text, buttons with names', async () => {
    const slot = { id: 4, label: 'Wachführung', min: 1, max: 1, rule: {}, rule_summary: null, position: 0, seated: 0 }
    const staffing = { met: false, required: 1, fulfilled: 0, missing: [{ label: 'Wachführung', count: 1 }], text: 'Mindestbesetzung: 0 von 1 erfüllt – es fehlt 1× Wachführung', slots: [{ id: 4, label: 'Wachführung', min: 1, max: 1, seated: 0, free: 1, missing: 1 }] }
    const wrapper = await mountPanel({ slots: [slot], extra_places: 1, max_participants: 2, staffing })
    expect(wrapper.text()).toContain('Positionen und Mindestbesetzung')
    expect(wrapper.text()).toContain('es fehlt 1× Wachführung')
    const max = wrapper.get('#part-max')
    expect(max.attributes('disabled')).toBeDefined()
    expect((max.element as HTMLInputElement).value).toBe('2')
    expect(wrapper.find('button[aria-label="Wachführung entfernen"]').exists()).toBe(true)
    await wrapper.findAll('button').find(b => b.text().includes('Position hinzufügen'))!.trigger('click')
    await wrapper.get('#slot-1-label').setValue('Trupp')
    await wrapper.get('#slot-1-max').setValue('3')
    expect((wrapper.get('#part-max').element as HTMLInputElement).value).toBe('5')
    expect(wrapper.text()).toContain('Plätze gesamt: 5')
  })

  it('enables capacity fields in opt_in and disables them with an explanation in opt_out', async () => {
    const wrapper = await mountPanel()
    const max = () => wrapper.find<HTMLInputElement>('#part-max')
    expect(max().element.disabled).toBe(false)
    expect(max().element.value).toBe('12')

    await wrapper.find('input[type="radio"][value="opt_out"]').setValue()
    expect(max().element.disabled).toBe(true)
    expect(max().element.value).toBe('')
    expect(wrapper.find<HTMLInputElement>('#part-min').element.disabled).toBe(true)
    expect(wrapper.find<HTMLSelectElement>('#part-waitlist').element.disabled).toBe(true)
    expect(wrapper.find('#part-capacity-note').text()).toContain('Im Modus „Abmeldung“')

    await wrapper.find('input[type="radio"][value="assignment"]').setValue()
    expect(max().element.disabled).toBe(false)
    expect(wrapper.text()).toContain('im Reiter „Zuteilung“')
  })

  it('shows the live preview count and enables saving only with changes', async () => {
    const wrapper = await mountPanel()
    expect(wrapper.text()).toContain('18 von 41 Personen der Zielgruppe erfüllen die Voraussetzungen')
    const save = () => wrapper.findAll('button').find(b => b.text() === 'Speichern')!
    expect(save().attributes('disabled')).toBeDefined()
    await wrapper.find('#part-note').setValue('Treffpunkt 17:30')
    expect(save().attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).toContain('Ungespeicherte Änderungen')
  })

  it('shows the 409 message with the choice between draft and server version', async () => {
    const wrapper = await mountPanel()
    api.saveConfig.mockRejectedValue(Object.assign(new Error('x'), { response: { status: 409, data: { code: 'stale', current: config({ revision: 2 }) } } }))
    await wrapper.find('#part-note').setValue('x')
    await wrapper.findAll('button').find(b => b.text() === 'Speichern')!.trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('zwischenzeitlich von jemand anderem geändert')
    expect(wrapper.text()).toContain('Neue Fassung laden und Entwurf verwerfen')
  })

  it('disables all inputs for read-only viewers', async () => {
    api.config.mockResolvedValue({ data: config() } as never)
    api.preview.mockResolvedValue({ data: { summary: '', total: 0, eligible: 0, excluded: [], errors: {}, audience_notice: null } } as never)
    const wrapper = mount(ParticipationSettings, { props: { sessionId: 7, readonly: true }, global: { plugins: [PrimeVue] } })
    await flushPromises()
    expect(wrapper.findAll('fieldset[disabled]').length).toBeGreaterThan(2)
    expect(wrapper.text()).not.toContain('Speichern')
  })
})
