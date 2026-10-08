import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ChangeRequestsTab from '../ChangeRequestsTab.vue'
import { changeRequestsApi } from '@/api/changeRequests'
import type { Review } from '@/types/changeRequests'

vi.mock('@/api/changeRequests', () => ({ changeRequestsApi: { reviews: vi.fn(), decide: vi.fn() } }))
const route = vi.hoisted(() => ({ query: {} as Record<string, string> }))
vi.mock('vue-router', () => ({ useRoute: () => route }))

function review(over: Partial<Review> = {}): Review {
  return {
    id: 1, kind: 'member', target_id: 2, person_name: 'Mia Becker', status: 'open', status_label: 'Offen', version: 3, requested_by: 'Sandra Becker', own: false,
    fields: [
      { field: 'mobile', label: 'Mobil', old: '0151', current: '0151', new: '0170', conflict: false },
      { field: 'email', label: 'E-Mail', old: '', current: 'neu@example.invalid', new: 'mia@example.invalid', conflict: true },
    ],
    decision_note: '', created_at: '2026-10-06T16:22:00Z', updated_at: '2026-10-06T16:22:00Z', decided_at: null, ...over,
  }
}

async function render(reviews: Review[]) {
  vi.mocked(changeRequestsApi.reviews).mockResolvedValue({ data: { results: reviews } } as never)
  const w = mount(ChangeRequestsTab, { global: { plugins: [PrimeVue] } })
  await flushPromises()
  return w
}
const radio = (w: Awaited<ReturnType<typeof render>>, field: string, text: string) =>
  w.get(`[data-field="${field}"]`).findAll('button[role="radio"]').find(b => b.text() === text)!
const submit = (w: Awaited<ReturnType<typeof render>>) => w.findAll('button').find(b => b.text().startsWith('Entscheidung speichern'))!

describe('ChangeRequestsTab', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks(); route.query = {} })

  it('opens the request named in a link from the inbox or a mail', async () => {
    route.query = { tab: 'antraege', antrag: '7' }
    const w = await render([review(), review({ id: 7, person_name: 'Ben Roth' })])
    expect(w.get('nav button[aria-current="true"]').text()).toContain('Ben Roth')
  })

  it('lists open requests with requester, field count and conflict marker', async () => {
    const w = await render([review()])
    expect(changeRequestsApi.reviews).toHaveBeenCalledWith('open')
    const item = w.get('nav button')
    expect(item.text()).toContain('Mia Becker')
    expect(item.text()).toContain('von Sandra Becker')
    expect(item.text()).toContain('2 Felder')
    expect(item.text()).toContain('1 Konflikt')
  })

  it('requires an explicit confirmation before a conflicting field can be applied', async () => {
    const w = await render([review()])
    expect(radio(w, 'email', 'Übernehmen').attributes('disabled')).toBeDefined()
    expect(w.get('[data-field="email"]').text()).toContain('Seit Antrag geändert')
    await radio(w, 'mobile', 'Übernehmen').trigger('click')
    await radio(w, 'email', 'Ablehnen').trigger('click')
    expect(submit(w).attributes('disabled')).toBeUndefined()

    await w.get('[data-field="email"] input[type="checkbox"]').setValue(true)
    expect(radio(w, 'email', 'Übernehmen').attributes('disabled')).toBeUndefined()
    await radio(w, 'email', 'Übernehmen').trigger('click')
    vi.mocked(changeRequestsApi.decide).mockResolvedValue({ data: review({ status: 'applied' }) } as never)
    await w.get('textarea').setValue(' Danke ')
    await submit(w).trigger('click')
    await flushPromises()
    expect(changeRequestsApi.decide).toHaveBeenCalledWith(1, { version: 3, decisions: { mobile: 'apply', email: 'apply' }, confirm_conflicts: ['email'], note: 'Danke' })
  })

  it('keeps the submit disabled while fields are undecided and "Alle übernehmen" skips unconfirmed conflicts', async () => {
    const w = await render([review()])
    expect(submit(w).text()).toContain('(2 offen)')
    expect(submit(w).attributes('disabled')).toBeDefined()
    await w.findAll('button').find(b => b.text() === 'Alle übernehmen')!.trigger('click')
    expect(radio(w, 'mobile', 'Übernehmen').attributes('aria-checked')).toBe('true')
    expect(radio(w, 'email', 'Übernehmen').attributes('aria-checked')).toBe('false')
    expect(submit(w).text()).toContain('(1 offen)')
    await w.findAll('button').find(b => b.text() === 'Alle ablehnen')!.trigger('click')
    expect(submit(w).attributes('disabled')).toBeUndefined()
  })

  it('disables deciding for own requests and says why', async () => {
    const w = await render([review({ own: true })])
    expect(w.text()).toContain('Eigene Anträge gibt eine andere Person frei.')
    expect(radio(w, 'mobile', 'Übernehmen').attributes('disabled')).toBeDefined()
    expect(radio(w, 'mobile', 'Ablehnen').attributes('disabled')).toBeDefined()
    expect(submit(w).attributes('disabled')).toBeDefined()
    expect(w.get('nav').text()).toContain('eigener Antrag')
  })

  it('reloads and tells the reviewer when the request is outdated', async () => {
    const w = await render([review()])
    await w.findAll('button').find(b => b.text() === 'Alle ablehnen')!.trigger('click')
    vi.mocked(changeRequestsApi.decide).mockRejectedValue({ response: { status: 409, data: { code: 'outdated', detail: 'x' } } })
    vi.mocked(changeRequestsApi.reviews).mockResolvedValue({ data: { results: [review({ version: 4, fields: [{ field: 'mobile', label: 'Mobil', old: '0151', current: '0151', new: '0180', conflict: false }] })] } } as never)
    await submit(w).trigger('click')
    await flushPromises()
    expect(w.get('[role="alert"]').text()).toContain('inzwischen geändert')
    expect(changeRequestsApi.reviews).toHaveBeenCalledTimes(2)
    expect(w.text()).toContain('0180')
    // Decisions start fresh for the new version.
    expect(submit(w).text()).toContain('(1 offen)')
  })

  it('shows the conflict message when the server rejects unconfirmed overwrites', async () => {
    const w = await render([review()])
    await w.findAll('button').find(b => b.text() === 'Alle ablehnen')!.trigger('click')
    vi.mocked(changeRequestsApi.decide).mockRejectedValue({ response: { status: 409, data: { code: 'conflict', detail: 'x', fields: { email: 'Konflikt' } } } })
    await submit(w).trigger('click')
    await flushPromises()
    expect(w.get('[role="alert"]').text()).toContain('Es wurde nichts übernommen')
  })

  it('shows decided requests read-only', async () => {
    const decided = review({ status: 'partial', status_label: 'Teilweise übernommen', decided_at: '2026-10-07T08:00:00Z', decision_note: 'Okay', fields: [{ field: 'mobile', label: 'Mobil', old: '0151', current: '0170', new: '0170', conflict: false, decision: 'apply' }] })
    const w = await render([review()])
    vi.mocked(changeRequestsApi.reviews).mockResolvedValue({ data: { results: [decided] } } as never)
    await w.findAll('nav,[role="group"]').length
    await w.findAll('[role="group"] button').find(b => b.text().startsWith('Entschieden'))!.trigger('click')
    await flushPromises()
    expect(changeRequestsApi.reviews).toHaveBeenLastCalledWith('decided')
    expect(w.text()).toContain('Übernommen')
    expect(w.text()).toContain('Teilweise übernommen')
    expect(w.findAll('button').some(b => b.text().startsWith('Entscheidung speichern'))).toBe(false)
  })
})
