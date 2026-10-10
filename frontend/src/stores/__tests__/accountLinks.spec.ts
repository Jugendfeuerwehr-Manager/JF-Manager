import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAccountLinksStore } from '../accountLinks'
import { accountLinksApi } from '@/api/accountLinks'

vi.mock('@/api/accountLinks', () => ({
  accountLinksApi: {
    forRecord: vi.fn(), suggestions: vi.fn(), searchAccounts: vi.fn(), link: vi.fn(), unlink: vi.fn(),
    pendingForMe: vi.fn(), confirm: vi.fn(), reject: vi.fn(), requestRelease: vi.fn(), duplicates: vi.fn(), mergeQualifications: vi.fn(),
  },
}))
const api = vi.mocked(accountLinksApi)
const apiError = (status: number, code: string, detail: string) => Object.assign(new Error(code), { response: { status, data: { code, detail } } })
const link = { id: 5, status: 'pending', user: { id: 2, username: 'leitung', name: 'Tobias Lehmann' }, member: null, parent: null, linked_by: 'Alex', linked_at: '', confirmed_at: null, rejected_at: null }

describe('accountLinks store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads the link of a record', async () => {
    api.forRecord.mockResolvedValue({ data: { results: [link] } } as never)
    const store = useAccountLinksStore()
    await store.load('member', 7)
    expect(api.forRecord).toHaveBeenCalledWith('member', 7)
    expect(store.link?.id).toBe(5)
    expect(store.error).toBeNull()
  })

  it('distinguishes missing rights from an empty result', async () => {
    api.forRecord.mockRejectedValue(apiError(403, 'x', 'Nein'))
    const store = useAccountLinksStore()
    await store.load('parent', 3)
    expect(store.error).toBe('forbidden')
    expect(store.link).toBeNull()
  })

  it('links the record and reports conflicts with their code', async () => {
    api.forRecord.mockResolvedValue({ data: { results: [] } } as never)
    const store = useAccountLinksStore()
    await store.load('member', 7)
    api.link.mockResolvedValue({ data: link } as never)
    expect(await store.linkAccount(2)).toEqual({ ok: true })
    expect(api.link).toHaveBeenCalledWith({ user: 2, member: 7, transfer: false })
    api.link.mockRejectedValue(apiError(409, 'record_linked', 'Schon verknüpft'))
    expect(await store.linkAccount(3)).toEqual({ ok: false, code: 'record_linked', message: 'Schon verknüpft' })
  })

  it('releases only the record in view', async () => {
    api.forRecord.mockResolvedValue({ data: { results: [link] } } as never)
    api.unlink.mockResolvedValue({ data: '' } as never)
    const store = useAccountLinksStore()
    await store.load('parent', 9)
    expect((await store.unlink()).ok).toBe(true)
    expect(api.unlink).toHaveBeenCalledWith(5, 'parent')
    expect(store.link).toBeNull()
  })

  it('loads duplicates silently and merges the chosen ones (PORTAL-04.4)', async () => {
    const row = { type: 'Erste Hilfe', account: { id: 4, acquired: null, expires: null, attachments: 0 }, member: { id: 5, acquired: null, expires: null, attachments: 0 }, same_date: true }
    api.duplicates.mockResolvedValue({ data: { link: 1, results: [row] } } as never)
    const store = useAccountLinksStore()
    await store.loadDuplicates(7)
    expect(store.duplicates).toHaveLength(1)
    api.mergeQualifications.mockResolvedValue({ data: { merged: 1, results: [] } } as never)
    expect((await store.mergeDuplicates(7, [4])).ok).toBe(true)
    expect(api.mergeQualifications).toHaveBeenCalledWith(7, [4])
    expect(store.duplicates).toEqual([])
    api.duplicates.mockRejectedValue(apiError(403, 'x', 'Nein'))
    await store.loadDuplicates(8)
    expect(store.duplicates).toEqual([])
    api.mergeQualifications.mockRejectedValue(apiError(403, 'own_record', 'Eigene Nachweise'))
    expect(await store.mergeDuplicates(8, [4])).toEqual({ ok: false, code: 'own_record', message: 'Eigene Nachweise' })
  })

  it('keeps only the newest search result', async () => {
    let resolveFirst: (v: unknown) => void = () => {}
    api.searchAccounts.mockReturnValueOnce(new Promise(r => { resolveFirst = r }) as never)
    api.searchAccounts.mockResolvedValueOnce({ data: { results: [{ id: 2, username: 'b', name: 'B', reason: '', linked: false }] } } as never)
    const store = useAccountLinksStore()
    const first = store.search('a')
    await store.search('b')
    resolveFirst({ data: { results: [{ id: 1, username: 'a', name: 'A', reason: '', linked: false }] } })
    await first
    expect(store.searchResults.map(r => r.id)).toEqual([2])
  })
})
