import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePortalAdminStore } from '../portalAdmin'
import { portalAdminApi } from '@/api/portalAdmin'

vi.mock('@/api/portalAdmin', () => ({
  portalAdminApi: {
    records: vi.fn(), detail: vi.fn(), invite: vi.fn(), resend: vi.fn(), revoke: vi.fn(), invitations: vi.fn(),
    bulkInvite: vi.fn(), suspend: vi.fn(), resume: vi.fn(), end: vi.fn(), extend: vi.fn(), ending: vi.fn(),
  },
}))
const api = vi.mocked(portalAdminApi)
const page = (results: unknown[] = []) => ({ data: { count: results.length, next: null, previous: null, results } }) as never
const apiError = (status: number, code: string, detail: string) => Object.assign(new Error(code), { response: { status, data: { code, detail } } })

describe('portalAdmin store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.records.mockResolvedValue(page())
    api.invitations.mockResolvedValue(page())
    api.ending.mockResolvedValue({ data: [] } as never)
  })

  it('loads records with kind, state and search filters and resets the selection', async () => {
    api.records.mockResolvedValue(page([{ kind: 'parent', id: 1, name: 'A', email: 'a@x.de', state: 'none', children: [] }]))
    const store = usePortalAdminStore()
    store.toggleSelected(1, true)
    await store.setFilter({ state: 'none', search: ' Anna ' })
    expect(api.records).toHaveBeenLastCalledWith({ kind: 'parent', state: 'none', search: 'Anna', limit: 20, offset: 0 })
    expect(store.records).toHaveLength(1)
    expect(store.selected).toEqual([])
  })

  it('reports a load error', async () => {
    api.records.mockRejectedValue(apiError(500, 'x', 'Server kaputt'))
    const store = usePortalAdminStore()
    await store.loadRecords()
    expect(store.error).toBe('Server kaputt')
    expect(store.loading).toBe(false)
  })

  it('maps invite error codes to the result', async () => {
    api.invite.mockRejectedValue(apiError(400, 'email_missing', 'Keine E-Mail'))
    const store = usePortalAdminStore()
    const result = await store.invite(3)
    expect(result).toEqual({ ok: false, code: 'email_missing', message: 'Keine E-Mail' })
    expect(store.busy).toBe(false)
    api.invite.mockRejectedValue(apiError(409, 'invitation_open', 'Offen'))
    expect((await store.invite(3)).code).toBe('invitation_open')
  })

  it('reloads lists after a successful invite', async () => {
    api.invite.mockResolvedValue({ data: {} } as never)
    const store = usePortalAdminStore()
    expect((await store.invite(3)).ok).toBe(true)
    expect(api.records).toHaveBeenCalled()
    expect(api.invitations).toHaveBeenCalled()
  })

  it('sends only inviteable selected parents in bulk and keeps the result summary', async () => {
    api.records.mockResolvedValue(page([
      { kind: 'parent', id: 1, name: 'A', email: 'a@x.de', state: 'none', children: [] },
      { kind: 'parent', id: 2, name: 'B', email: 'b@x.de', state: 'active', children: [] },
    ]))
    api.bulkInvite.mockResolvedValue({ data: { results: [{ parent: 1, result: 'sent' }, { parent: 5, result: 'skipped', code: 'email_missing', detail: 'x' }] } } as never)
    const store = usePortalAdminStore()
    await store.loadRecords()
    store.toggleSelected(1, true); store.toggleSelected(2, true)
    expect(store.inviteableSelected).toEqual([1])
    await store.bulkInvite()
    expect(api.bulkInvite).toHaveBeenCalledWith([1])
    expect(store.bulkResults?.map(r => r.result)).toEqual(['sent', 'skipped'])
    expect(store.selected).toEqual([])
  })

  it('suspends and ends access by subject', async () => {
    api.suspend.mockResolvedValue({ data: {} } as never)
    api.end.mockRejectedValue(apiError(409, 'no_access', 'Kein Zugang'))
    const store = usePortalAdminStore()
    expect((await store.suspend({ parent: 4 })).ok).toBe(true)
    expect(api.suspend).toHaveBeenCalledWith({ parent: 4 })
    expect(await store.endAccess({ member: 9 })).toMatchObject({ ok: false, code: 'no_access' })
  })

  it('returns the server message for extension errors', async () => {
    api.extend.mockRejectedValue(apiError(400, 'too_long', 'Zu lang'))
    const store = usePortalAdminStore()
    expect(await store.extend({ parent: 1, member: 2, until: '2030-01-01', reason: 'x' })).toMatchObject({ ok: false, code: 'too_long', message: 'Zu lang' })
  })

  it('lists open invitations before expired and finished ones', async () => {
    const inv = (id: number, state: string) => ({ id, state })
    api.invitations.mockResolvedValue(page([inv(1, 'accepted'), inv(2, 'expired'), inv(3, 'open')]))
    const store = usePortalAdminStore()
    await store.loadInvitations()
    expect(store.invitations.map(i => i.id)).toEqual([3, 2, 1])
  })

  it('invites a member through the member payload and surfaces the server reason on 422', async () => {
    api.invite.mockRejectedValue(apiError(422, 'member_portal_disabled', 'Das Mitgliederportal ist für dieses Mitglied nicht freigegeben.'))
    const store = usePortalAdminStore()
    const result = await store.invite(9, 'member')
    expect(api.invite).toHaveBeenCalledWith(9, 'member')
    expect(result).toEqual({ ok: false, code: 'member_portal_disabled', message: 'Das Mitgliederportal ist für dieses Mitglied nicht freigegeben.' })
  })
})
