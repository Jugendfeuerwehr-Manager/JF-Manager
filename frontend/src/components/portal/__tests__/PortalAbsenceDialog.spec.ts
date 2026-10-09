import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import PortalAbsenceDialog from '../PortalAbsenceDialog.vue'
import { portalApi } from '@/api/portal'
import { usePortalStore } from '@/stores/portal'

vi.mock('@/api/portal', () => ({ portalApi: { previewAbsence: vi.fn(), createAbsence: vi.fn(), sessions: vi.fn() } }))
vi.mock('@/router', () => ({ default: { push: vi.fn() } }))

const mia = { id: 2, relation: 'child' as const, first_name: 'Mia', last_name: 'B' }
let wrapper: VueWrapper | null = null
const button = (w: VueWrapper, label: string) => w.findAll('button').find(b => b.text() === label)!

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  const store = usePortalStore()
  store.selectedPersonId = 2
  vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 2, sessions: [] } } as never)
  wrapper = mount(PortalAbsenceDialog, { props: { person: mia }, global: { plugins: [PrimeVue] }, attachTo: document.body })
})
afterEach(() => { wrapper?.unmount() })

describe('PortalAbsenceDialog', () => {
  it('needs a valid range before the preview and blocks confirming without one', async () => {
    const w = wrapper!
    expect(button(w, 'Vorschau anzeigen').attributes('disabled')).toBeDefined()
    expect(button(w, 'Abmeldung senden').attributes('disabled')).toBeDefined()
    await w.get('#absence-from').setValue('2026-10-20')
    await w.get('#absence-to').setValue('2026-10-10')
    expect(button(w, 'Vorschau anzeigen').attributes('disabled')).toBeDefined()
  })

  it('shows what is cancelled and what is skipped, then confirms', async () => {
    vi.mocked(portalApi.previewAbsence).mockResolvedValue({ data: { person: 2, will_cancel: 1, skipped: 1, sessions: [
      { id: 1, title: 'Knoten', date: '2026-10-14', start_time: '18:00:00', end_time: '20:00:00', place: '', state: 'none', action: 'cancel', skip: null },
      { id: 2, title: 'Marsch', date: '2026-10-18', start_time: '09:00:00', end_time: null, place: '', state: 'none', action: 'skip', skip: { code: 'deadline_passed', detail: 'Abmeldung nur noch direkt bei der Dienstleitung.' } },
    ] } } as never)
    vi.mocked(portalApi.createAbsence).mockResolvedValue({ data: { person: 2, cancelled: [{ id: 1 }], skipped: [] } } as never)
    const w = wrapper!
    await w.get('#absence-from').setValue('2026-10-10')
    await w.get('#absence-to').setValue('2026-10-20')
    await w.findAll('input[type="radio"]')[2]!.setValue(true)
    await button(w, 'Vorschau anzeigen').trigger('click')
    await flushPromises()
    expect(portalApi.previewAbsence).toHaveBeenCalledWith(expect.objectContaining({ person: 2, from: '2026-10-10', to: '2026-10-20' }))
    const text = w.get('[aria-label="Vorschau"]').text()
    expect(text).toContain('Wird abgemeldet (1)')
    expect(text).toContain('Knoten')
    expect(text).toContain('Wird übersprungen (1)')
    expect(text).toContain('Marsch')
    expect(text).toContain('Abmeldung nur noch direkt bei der Dienstleitung.')
    await button(w, 'Abmeldung senden').trigger('click')
    await flushPromises()
    expect(portalApi.createAbsence).toHaveBeenCalledWith({ person: 2, from: '2026-10-10', to: '2026-10-20', reason_category: 'urlaub', reason_note: '' })
    expect(w.emitted('done')).toHaveLength(1)
  })

  it('drops the preview when the range changes and shows server errors', async () => {
    vi.mocked(portalApi.previewAbsence).mockResolvedValueOnce({ data: { person: 2, will_cancel: 0, skipped: 0, sessions: [] } } as never)
    const w = wrapper!
    await w.get('#absence-from').setValue('2026-10-10')
    await w.get('#absence-to').setValue('2026-10-20')
    await button(w, 'Vorschau anzeigen').trigger('click')
    await flushPromises()
    expect(w.text()).toContain('In diesem Zeitraum gibt es keine Dienste.')
    await w.get('#absence-to').setValue('2026-10-25')
    expect(w.find('[aria-label="Vorschau"]').exists()).toBe(false)
    vi.mocked(portalApi.previewAbsence).mockRejectedValueOnce(Object.assign(new Error('x'), { response: { status: 429, data: {} } }))
    await button(w, 'Vorschau anzeigen').trigger('click')
    await flushPromises()
    expect(w.get('[role="alert"]').text()).toBe('Bitte kurz warten und erneut versuchen.')
  })
})
