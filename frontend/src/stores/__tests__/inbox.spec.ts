import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { COUNTS_POLL_MS, useInboxStore } from '../inbox'
import { inboxApi, inboxParams, type InboxEntry } from '@/api/inbox'

vi.mock('@/api/inbox', async (orig) => ({
  ...(await orig<typeof import('@/api/inbox')>()),
  inboxApi: { list: vi.fn(), counts: vi.fn(), markRead: vi.fn(), markReadBulk: vi.fn(), markDone: vi.fn() },
}))

const entry = (id: number, extra: Partial<InboxEntry> = {}): InboxEntry => ({
  id, kind: 'k', category: 'requests', type: 'task', title: `T${id}`, count: 1, link: '/x', department: 'Mitte', department_id: 1,
  updated_at: '2026-10-08T10:00:00Z', created_at: '2026-10-08T10:00:00Z', read: false, task_state: 'open', done_by: null, done_at: null, done_via: null, ...extra,
})
const counts = (total: number) => ({ data: { open_tasks: total, unread_notices: 0, total } })

describe('inbox store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers()
    vi.mocked(inboxApi.list).mockResolvedValue({ data: { count: 2, results: [entry(1), entry(2)] } } as never)
    vi.mocked(inboxApi.counts).mockResolvedValue(counts(2) as never)
  })
  afterEach(() => { vi.useRealTimers() })

  it('maps filters to query parameters and omits unset ones', async () => {
    expect(inboxParams({ type: '', category: '', department: null, unread: false, done: false })).toEqual({})
    expect(inboxParams({ type: 'task', category: 'staffing', department: 3, unread: true, done: true, offset: 50 }))
      .toEqual({ type: 'task', category: 'staffing', department: 3, unread: 1, done: 1, offset: 50 })
    const store = useInboxStore()
    await store.setFilters({ type: 'notice', unread: true })
    expect(inboxApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ type: 'notice', unread: true, offset: 0 }))
    expect(store.entries).toHaveLength(2)
  })

  it('appends further pages with the current offset', async () => {
    const store = useInboxStore()
    vi.mocked(inboxApi.list).mockResolvedValueOnce({ data: { count: 3, results: [entry(1), entry(2)] } } as never)
    await store.fetchEntries()
    expect(store.hasMore).toBe(true)
    vi.mocked(inboxApi.list).mockResolvedValueOnce({ data: { count: 3, results: [entry(3)] } } as never)
    await store.fetchEntries(true)
    expect(inboxApi.list).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 2 }))
    expect(store.entries.map(e => e.id)).toEqual([1, 2, 3])
  })

  it('polls counts every 60 s only while the tab is visible and stops on request', async () => {
    const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
    const store = useInboxStore()
    store.startPolling()
    expect(inboxApi.counts).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(COUNTS_POLL_MS)
    expect(inboxApi.counts).toHaveBeenCalledTimes(2)
    visibility.mockReturnValue('hidden')
    await vi.advanceTimersByTimeAsync(COUNTS_POLL_MS * 2)
    expect(inboxApi.counts).toHaveBeenCalledTimes(2)
    visibility.mockReturnValue('visible')
    document.dispatchEvent(new Event('visibilitychange'))
    expect(inboxApi.counts).toHaveBeenCalledTimes(3)
    store.stopPolling()
    await vi.advanceTimersByTimeAsync(COUNTS_POLL_MS * 2)
    expect(inboxApi.counts).toHaveBeenCalledTimes(3)
    expect(store.counts.total).toBe(2)
    visibility.mockRestore()
  })

  it('takes read and done state from the server response', async () => {
    const store = useInboxStore()
    await store.fetchEntries()
    vi.mocked(inboxApi.markRead).mockResolvedValue({ data: entry(1, { read: true }) } as never)
    await store.markRead(1)
    expect(store.entries[0]!.read).toBe(true)

    const finished = entry(2, { task_state: 'done', done_by: 'A. Keller', done_via: 'ui', read: true })
    vi.mocked(inboxApi.markDone).mockResolvedValue({ data: finished } as never)
    await store.markDone(2)
    expect(store.entries.map(e => e.id)).toEqual([1])

    await store.setFilters({ done: true })
    vi.mocked(inboxApi.markDone).mockResolvedValue({ data: finished } as never)
    await store.markDone(2)
    expect(store.entries.find(e => e.id === 2)!.task_state).toBe('done')
    expect(inboxApi.counts).toHaveBeenCalled()
  })

  it('marks a selection as read in one request', async () => {
    const store = useInboxStore()
    await store.fetchEntries()
    store.toggleSelected(1)
    store.toggleSelected(2)
    store.toggleSelected(2)
    vi.mocked(inboxApi.markReadBulk).mockResolvedValue({ data: { updated: 1 } } as never)
    expect(await store.markReadBulk()).toBe(1)
    expect(inboxApi.markReadBulk).toHaveBeenCalledWith([1])
    expect(store.entries.map(e => e.read)).toEqual([true, false])
    expect(store.selected).toEqual([])
  })
})
