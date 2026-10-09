import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { portalApi } from '@/api/portal'
import { usePortalStore } from '../portal'
import { makeItem } from '@/utils/__tests__/portalFixtures'

vi.mock('@/api/portal', () => ({
  portalApi: { me: vi.fn(), sessions: vi.fn(), setRegistration: vi.fn(), previewAbsence: vi.fn(), createAbsence: vi.fn() },
}))
vi.mock('@/router', () => ({ default: { push: vi.fn() } }))

const fail = (status: number, data: unknown = {}) => Object.assign(new Error('x'), { response: { status, data } })

function setup() {
  setActivePinia(createPinia())
  const store = usePortalStore()
  store.me = { account: { first_name: 'A', last_name: 'B', email: 'a@b.c' }, people: [{ id: 2, relation: 'child', first_name: 'Mia', last_name: 'B' }] }
  store.selectedPersonId = 2
  store.sessionsPersonId = 2
  return store
}

describe('portal store sessions', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('loads the sessions of the selected person', async () => {
    const store = setup()
    vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 2, sessions: [makeItem()] } } as never)
    await store.loadSessions()
    expect(portalApi.sessions).toHaveBeenCalledWith(2)
    expect(store.sessions).toHaveLength(1)
    expect(store.sessionsLoaded).toBe(true)
  })

  it('keeps an error message when loading fails and shows the throttle text on 429', async () => {
    const store = setup()
    vi.mocked(portalApi.sessions).mockRejectedValueOnce(fail(500, { detail: 'Kaputt' }))
    await store.loadSessions()
    expect(store.sessionsError).toBe('Kaputt')
    vi.mocked(portalApi.sessions).mockRejectedValueOnce(fail(429))
    await store.loadSessions()
    expect(store.sessionsError).toBe('Bitte kurz warten und erneut versuchen.')
  })

  it('only the newest load of a quickly switched person writes', async () => {
    const store = setup()
    let resolveFirst!: (v: unknown) => void
    vi.mocked(portalApi.sessions).mockImplementationOnce(() => new Promise(r => { resolveFirst = r }) as never)
    vi.mocked(portalApi.sessions).mockResolvedValueOnce({ data: { person: 3, sessions: [makeItem({ id: 9 })] } } as never)
    const first = store.loadSessions(2)
    await store.loadSessions(3)
    resolveFirst({ data: { person: 2, sessions: [makeItem({ id: 1 })] } })
    await first
    expect(store.sessions.map(s => s.id)).toEqual([9])
  })

  it('replaces the item with the server answer after a successful change', async () => {
    const store = setup()
    store.sessions = [makeItem({ version: 0 })]
    vi.mocked(portalApi.setRegistration).mockResolvedValue({ data: makeItem({ state: 'registered', version: 1, may_cancel: true, may_register: false }) } as never)
    const ok = await store.setRegistration(store.sessions[0]!, { target: 'registered' })
    expect(ok).toBe(true)
    expect(portalApi.setRegistration).toHaveBeenCalledWith(7, 2, { version: 0, target: 'registered' })
    expect(store.sessions[0]!.state).toBe('registered')
    expect(store.pendingSessionIds).toEqual([])
  })

  it('does not change the list on a failed change and exposes 422 reasons', async () => {
    const store = setup()
    store.sessions = [makeItem()]
    vi.mocked(portalApi.setRegistration).mockRejectedValue(fail(422, { code: 'not_eligible', detail: 'Die Voraussetzungen sind nicht erfüllt.', reasons: ['Alter: mindestens 15'] }))
    vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 2, sessions: [makeItem()] } } as never)
    const ok = await store.setRegistration(store.sessions[0]!, { target: 'registered' })
    expect(ok).toBe(false)
    expect(store.sessions[0]!.state).toBe('no_response')
    expect(store.actionError).toMatchObject({ sessionId: 7, code: 'not_eligible', reasons: ['Alter: mindestens 15'] })
  })

  it('reloads the list on a stale version (409) and explains it', async () => {
    const store = setup()
    store.sessions = [makeItem()]
    vi.mocked(portalApi.setRegistration).mockRejectedValue(fail(409, { code: 'stale', detail: 'Die Meldung wurde inzwischen geändert.' }))
    vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 2, sessions: [makeItem({ state: 'registered', version: 3 })] } } as never)
    await store.setRegistration(store.sessions[0]!, { target: 'registered' })
    expect(portalApi.sessions).toHaveBeenCalledTimes(1)
    expect(store.sessions[0]!.state).toBe('registered')
    expect(store.actionError?.code).toBe('stale')
    expect(store.actionError?.message).toContain('aktualisiert')
  })

  it('maps 429 to a wait message', async () => {
    const store = setup()
    store.sessions = [makeItem()]
    vi.mocked(portalApi.setRegistration).mockRejectedValue(fail(429))
    await store.setRegistration(store.sessions[0]!, { target: 'registered' })
    expect(store.actionError?.message).toBe('Bitte kurz warten und erneut versuchen.')
  })

  it('previews and creates an absence, then reloads', async () => {
    const store = setup()
    vi.mocked(portalApi.previewAbsence).mockResolvedValue({ data: { person: 2, sessions: [{ id: 7, action: 'cancel' }], will_cancel: 1, skipped: 0 } } as never)
    vi.mocked(portalApi.createAbsence).mockResolvedValue({ data: { person: 2, cancelled: [{ id: 7 }], skipped: [] } } as never)
    vi.mocked(portalApi.sessions).mockResolvedValue({ data: { person: 2, sessions: [] } } as never)
    expect(await store.previewAbsence({ from: '2026-10-10', to: '2026-10-20' })).toBe(true)
    expect(portalApi.previewAbsence).toHaveBeenCalledWith({ from: '2026-10-10', to: '2026-10-20', person: 2 })
    const result = await store.createAbsence({ from: '2026-10-10', to: '2026-10-20', reason_category: 'urlaub' })
    expect(result?.cancelled).toHaveLength(1)
    expect(portalApi.sessions).toHaveBeenCalled()
  })
})
