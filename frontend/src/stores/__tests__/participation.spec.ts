import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { PREVIEW_DELAY_MS, useParticipationStore } from '../participation'
import { participationApi, type ParticipationConfig, type Rule } from '@/api/participation'

vi.mock('@/api/participation', () => ({
  participationApi: {
    config: vi.fn(), saveConfig: vi.fn(), registrations: vi.fn(), setRegistration: vi.fn(), validate: vi.fn(), preview: vi.fn(),
  },
}))
const api = vi.mocked(participationApi)
const apiError = (status: number, data: Record<string, unknown>) => Object.assign(new Error('x'), { response: { status, data } })

const config = (over: Partial<ParticipationConfig> = {}): ParticipationConfig => ({
  session: 7, revision: 3, mode: 'opt_in', portal_visible: true, public_note: '',
  registration_opens_at: null, registration_closes_at: null, cancellation_closes_at: null,
  max_participants: 10, min_participants: null, waitlist_mode: 'auto', eligibility: {},
  effective: { start: '2030-01-01T18:00:00Z', registration_opens_at: null, registration_closes_at: '2029-12-30T18:00:00Z', cancellation_closes_at: '2030-01-01T16:00:00Z' },
  defaults: { mode: 'opt_out', registration_offset_h: 48, cancellation_offset_h: 2, waitlist_mode: 'auto' },
  eligibility_summary: null, audience_notice: null, ...over,
})
const rule = (age: number): Rule => ({ v: 1, match: 'all', rules: [{ kind: 'age', op: 'min', min: age }] })
const previewBody = (eligible = 1) => ({ data: { summary: 's', total: 2, eligible, excluded: [], errors: {}, audience_notice: null } }) as never

describe('participation store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
    api.config.mockResolvedValue({ data: config() } as never)
  })
  afterEach(() => { vi.useRealTimers() })

  it('loads the config into a draft and tracks dirty state', async () => {
    const store = useParticipationStore()
    await store.loadConfig(7)
    expect(store.dirty).toBe(false)
    expect(store.draft?.eligibility).toEqual({ v: 1, match: 'all', rules: [] })
    store.draft!.public_note = 'Treffpunkt'
    expect(store.dirty).toBe(true)
    store.discard()
    expect(store.dirty).toBe(false)
    expect(store.draft?.public_note).toBe('')
  })

  it('clears capacity when switching to opt_out', async () => {
    const store = useParticipationStore()
    await store.loadConfig(7)
    store.setMode('opt_out')
    expect(store.draft).toMatchObject({ mode: 'opt_out', max_participants: null, min_participants: null })
  })

  it('saves with the current revision and sends {} for an empty rule', async () => {
    api.saveConfig.mockResolvedValue({ data: config({ revision: 4, public_note: 'Neu' }) } as never)
    const store = useParticipationStore()
    await store.loadConfig(7)
    store.draft!.public_note = 'Neu'
    const result = await store.saveConfig()
    expect(result.ok).toBe(true)
    expect(api.saveConfig).toHaveBeenCalledWith(7, expect.objectContaining({ revision: 3, public_note: 'Neu', eligibility: {} }))
    expect(store.config?.revision).toBe(4)
    expect(store.dirty).toBe(false)
  })

  it('keeps the draft on a 409 and can save on top of the newer revision', async () => {
    const current = config({ revision: 9, public_note: 'Fremd' })
    api.saveConfig.mockRejectedValueOnce(apiError(409, { code: 'stale', detail: 'x', current }))
    const store = useParticipationStore()
    await store.loadConfig(7)
    store.draft!.public_note = 'Meins'
    const result = await store.saveConfig()
    expect(result).toMatchObject({ ok: false, code: 'stale' })
    expect(store.conflict?.revision).toBe(9)
    expect(store.draft?.public_note).toBe('Meins')
    store.keepDraftOnServerVersion()
    expect(store.config?.revision).toBe(9)
    expect(store.draft?.public_note).toBe('Meins')
    expect(store.dirty).toBe(true)
    api.saveConfig.mockResolvedValue({ data: config({ revision: 10, public_note: 'Meins' }) } as never)
    await store.saveConfig()
    expect(api.saveConfig).toHaveBeenLastCalledWith(7, expect.objectContaining({ revision: 9 }))
  })

  it('takes the server version when asked to', async () => {
    api.saveConfig.mockRejectedValueOnce(apiError(409, { code: 'stale', current: config({ revision: 9, public_note: 'Fremd' }) }))
    const store = useParticipationStore()
    await store.loadConfig(7)
    store.draft!.public_note = 'Meins'
    await store.saveConfig()
    store.useServerVersion()
    expect(store.draft?.public_note).toBe('Fremd')
    expect(store.conflict).toBeNull()
  })

  it('maps 400 field and rule errors', async () => {
    api.saveConfig.mockRejectedValue(apiError(400, {
      max_participants: ['Zu hoch'], eligibility: { 'rules[0].max': 'Mindestalter größer als Höchstalter' },
    }))
    const store = useParticipationStore()
    await store.loadConfig(7)
    store.draft!.public_note = 'x'
    const result = await store.saveConfig()
    expect(result.code).toBe('invalid')
    expect(store.fieldErrors.max_participants).toBe('Zu hoch')
    expect(store.ruleErrors['rules[0].max']).toBe('Mindestalter größer als Höchstalter')
  })

  it('debounces the preview and only sends the last rule', async () => {
    vi.useFakeTimers()
    api.preview.mockResolvedValue(previewBody(5))
    const store = useParticipationStore()
    await store.loadConfig(7)
    store.schedulePreview(rule(10))
    store.schedulePreview(rule(12))
    store.schedulePreview(rule(14))
    expect(api.preview).not.toHaveBeenCalled()
    expect(store.previewLoading).toBe(true)
    await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS)
    expect(api.preview).toHaveBeenCalledTimes(1)
    expect(api.preview).toHaveBeenCalledWith(rule(14), 7)
    expect(store.preview?.eligible).toBe(5)
    expect(store.previewLoading).toBe(false)
  })

  it('maps a 400 preview answer to row errors and drops the stale result', async () => {
    api.preview.mockRejectedValue(apiError(400, { errors: { 'rules[0].max': 'Mindestalter größer als Höchstalter' } }))
    const store = useParticipationStore()
    await store.loadConfig(7)
    await store.runPreview(rule(10))
    expect(store.ruleErrors).toEqual({ 'rules[0].max': 'Mindestalter größer als Höchstalter' })
    expect(store.preview).toBeNull()

    let release!: (value: unknown) => void
    api.preview.mockImplementationOnce(() => new Promise(resolve => { release = resolve }) as never)
    const slow = store.runPreview(rule(10))
    api.preview.mockResolvedValueOnce(previewBody(2))
    await store.runPreview(rule(11))
    release(previewBody(99))
    await slow
    expect(store.preview?.eligible).toBe(2)
  })

  it('reports a failing preview request without row errors', async () => {
    api.preview.mockRejectedValue(apiError(500, { detail: 'Server kaputt' }))
    const store = useParticipationStore()
    await store.loadConfig(7)
    await store.runPreview(rule(10))
    expect(store.previewError).toBe('Server kaputt')
    expect(store.ruleErrors).toEqual({})
  })

  it('sets a registration with the row version and reloads the list', async () => {
    const overview = { members: [{ member_id: 4, registration: { version: 6 } }], counts: {} }
    api.registrations.mockResolvedValue({ data: overview } as never)
    api.setRegistration.mockResolvedValue({ data: {} } as never)
    const store = useParticipationStore()
    await store.loadConfig(7)
    await store.loadRegistrations()
    const result = await store.setRegistration(4, 'cancelled', { category: 'krankheit', note: 'Grippe' })
    expect(result.ok).toBe(true)
    expect(api.setRegistration).toHaveBeenCalledWith(7, 4, {
      target: 'cancelled', reason_category: 'krankheit', reason_note: 'Grippe', version: 6, accept_waitlist: true,
    })
    expect(api.registrations).toHaveBeenCalledTimes(2)
    expect(store.busyMember).toBeNull()
  })

  it('returns the server code when a registration change is refused', async () => {
    api.registrations.mockResolvedValue({ data: { members: [], counts: {} } } as never)
    api.setRegistration.mockRejectedValue(apiError(422, { code: 'mode_forbidden', detail: 'Nicht möglich', reasons: [] }))
    const store = useParticipationStore()
    await store.loadConfig(7)
    const result = await store.setRegistration(4, 'registered')
    expect(result).toEqual({ ok: false, code: 'mode_forbidden', message: 'Nicht möglich' })
  })
})
