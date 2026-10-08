import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import PortalSessionList from '../PortalSessionList.vue'
import { portalApi } from '@/api/portal'
import { usePortalStore } from '@/stores/portal'
import { makeItem } from '@/utils/__tests__/portalFixtures'

vi.mock('@/api/portal', () => ({ portalApi: { sessions: vi.fn(), setRegistration: vi.fn(), previewAbsence: vi.fn(), createAbsence: vi.fn() } }))
vi.mock('@/router', () => ({ default: { push: vi.fn() } }))

let wrapper: VueWrapper | null = null
const mount_ = (props: Record<string, unknown> = {}) => {
  const store = usePortalStore()
  store.me = { account: { first_name: 'A', last_name: 'B', email: 'a@b.c' }, people: [{ id: 2, relation: 'child', first_name: 'Mia', last_name: 'B' }] }
  store.selectedPersonId = 2
  wrapper = mount(PortalSessionList, { props, global: { plugins: [PrimeVue], stubs: { RouterLink: { template: '<a><slot /></a>' } } }, attachTo: document.body })
  return wrapper
}
const btn = (w: VueWrapper, label: string) => w.findAll('button').find(b => b.text() === label)

beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })
afterEach(() => { wrapper?.unmount() })

describe('PortalSessionList', () => {
  it('shows the empty state without inventing data', async () => {
    vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 2, sessions: [] } } as never)
    const w = mount_(); await flushPromises()
    expect(w.text()).toContain('Noch keine geplanten Dienste')
  })

  it('shows an error with retry', async () => {
    vi.mocked(portalApi.sessions).mockRejectedValue(new Error('offline'))
    const w = mount_(); await flushPromises()
    expect(w.text()).toContain('Erneut versuchen')
  })

  it('registers Mia directly and swaps the card to the server state', async () => {
    vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 2, sessions: [makeItem()] } } as never)
    vi.mocked(portalApi.setRegistration).mockResolvedValue({ data: makeItem({ state: 'registered', may_cancel: true, may_register: false, version: 1 }) } as never)
    const w = mount_(); await flushPromises()
    expect(w.text()).toContain('Keine Rückmeldung')
    expect(w.text()).toContain('Noch 3 Plätze frei')
    await btn(w, 'Mia anmelden')!.trigger('click'); await flushPromises()
    expect(portalApi.setRegistration).toHaveBeenCalledWith(7, 2, { version: 0, target: 'registered', accept_waitlist: false })
    expect(w.find('[data-status="registered"]').exists()).toBe(true)
    expect(btn(w, 'Mia abmelden')).toBeTruthy()
  })

  it('cancels through the sheet with reason and note', async () => {
    vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 2, sessions: [makeItem({ state: 'registered', may_cancel: true, may_register: false })] } } as never)
    vi.mocked(portalApi.setRegistration).mockResolvedValue({ data: makeItem({ state: 'cancelled', may_register: true, reason_category: 'krankheit', version: 2 }) } as never)
    const w = mount_(); await flushPromises()
    await btn(w, 'Mia abmelden')!.trigger('click')
    expect(w.find('[role="dialog"]').exists()).toBe(true)
    await w.findAll('input[type="radio"]')[0]!.setValue(true)
    await btn(w, 'Abmeldung senden')!.trigger('click'); await flushPromises()
    expect(portalApi.setRegistration).toHaveBeenCalledWith(7, 2, { version: 0, target: 'cancelled', reason_category: 'krankheit', reason_note: '' })
    expect(w.find('[role="dialog"]').exists()).toBe(false)
    expect(w.text()).toContain('Grund: Krankheit')
  })

  it('keeps the sheet open and shows the server message when cancelling fails', async () => {
    vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 2, sessions: [makeItem({ state: 'registered', may_cancel: true, may_register: false })] } } as never)
    vi.mocked(portalApi.setRegistration).mockRejectedValue(Object.assign(new Error('x'), { response: { status: 422, data: { code: 'deadline_passed', detail: 'Abmeldung nur noch direkt bei der Dienstleitung.', reasons: [] } } }))
    const w = mount_(); await flushPromises()
    await btn(w, 'Mia abmelden')!.trigger('click')
    await btn(w, 'Abmeldung senden')!.trigger('click'); await flushPromises()
    expect(w.find('[role="dialog"]').exists()).toBe(true)
    expect(w.get('[role="dialog"] [role="alert"]').text()).toContain('Abmeldung nur noch direkt bei der Dienstleitung.')
  })

  it('shows not-eligible reasons on the card and no action', async () => {
    vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 2, sessions: [makeItem({ may_register: false, eligibility: { ok: false, reasons: ['Alter: mindestens 15'], audience_notice: null } })] } } as never)
    const w = mount_(); await flushPromises()
    expect(w.text()).toContain('Nicht möglich')
    expect(w.text()).toContain('Alter: mindestens 15')
    expect(btn(w, 'Mia anmelden')).toBeUndefined()
  })

  it('groups by month on the sessions page and limits on the overview', async () => {
    vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 2, sessions: [makeItem({ id: 1 }), makeItem({ id: 2, date: '2026-11-03' }), makeItem({ id: 3, date: '2026-11-10' })] } } as never)
    const grouped = mount_({ grouped: true }); await flushPromises()
    expect(grouped.findAll('h2').map(h => h.text())).toEqual(['Oktober 2026', 'November 2026'])
    grouped.unmount()
    const limited = mount_({ limit: 2 }); await flushPromises()
    expect(limited.findAll('article')).toHaveLength(2)
  })
})
