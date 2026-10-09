import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePortalStore } from '../portal'
import { portalApi } from '@/api/portal'

vi.mock('@/api/portal', () => ({ portalApi: { me: vi.fn(), invitationInfo: vi.fn(), acceptInvitation: vi.fn() } }))
vi.mock('@/router', () => ({ default: { push: vi.fn(), currentRoute: { value: { path: '/' } } } }))

const apiError = (status: number, data: Record<string, unknown>) => ({ response: { status, data } })
const payload = { token: 't', password: 'pw', password_confirm: 'pw', privacy_accepted: true }

describe('portal store invitation', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('loads invitation info', async () => {
    const data = { email: 'a@b.de', kind: 'parent', expires_at: '2030-01-01T00:00:00Z' }
    vi.mocked(portalApi.invitationInfo).mockResolvedValue({ data } as never)
    const store = usePortalStore()
    await store.loadInvitation('t')
    expect(portalApi.invitationInfo).toHaveBeenCalledWith('t')
    expect(store.invitation).toEqual(data)
    expect(store.invitationError).toBeNull()
  })

  it('keeps the error code for expired invitations', async () => {
    vi.mocked(portalApi.invitationInfo).mockRejectedValue(apiError(410, { detail: 'Abgelaufen.', code: 'expired' }))
    const store = usePortalStore()
    await store.loadInvitation('t')
    expect(store.invitationError).toEqual({ code: 'expired', message: 'Abgelaufen.' })
    expect(store.invitation).toBeNull()
  })

  it('treats a missing token as invalid without calling the API', async () => {
    const store = usePortalStore()
    await store.loadInvitation('')
    expect(store.invitationError?.code).toBe('invalid')
    expect(portalApi.invitationInfo).not.toHaveBeenCalled()
  })

  it('accepts an invitation', async () => {
    vi.mocked(portalApi.acceptInvitation).mockResolvedValue({ data: { username: 'a@b.de' } } as never)
    const store = usePortalStore()
    expect(await store.acceptInvitation(payload)).toBe(true)
    expect(store.accepted).toBe(true)
  })

  it('maps field errors', async () => {
    vi.mocked(portalApi.acceptInvitation).mockRejectedValue(
      apiError(400, { password: ['Zu kurz.'], privacy_accepted: ['Pflicht.'] }),
    )
    const store = usePortalStore()
    expect(await store.acceptInvitation(payload)).toBe(false)
    expect(store.acceptFieldErrors).toEqual({ password: 'Zu kurz.', privacy_accepted: 'Pflicht.' })
    expect(store.accepted).toBe(false)
  })

  it('handles a plain password error with code', async () => {
    vi.mocked(portalApi.acceptInvitation).mockRejectedValue(apiError(400, { password: 'Zu einfach.', code: 'password' }))
    const store = usePortalStore()
    await store.acceptInvitation(payload)
    expect(store.acceptFieldErrors).toEqual({ password: 'Zu einfach.' })
  })

  it('shows expired state when accept returns 410', async () => {
    vi.mocked(portalApi.acceptInvitation).mockRejectedValue(apiError(410, { detail: 'Abgelaufen.', code: 'expired' }))
    const store = usePortalStore()
    await store.acceptInvitation(payload)
    expect(store.invitationError?.code).toBe('expired')
    expect(store.acceptError).toBe('Abgelaufen.')
  })
})
