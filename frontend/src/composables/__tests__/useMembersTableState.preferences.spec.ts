import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useMembersTableState } from '../useMembersTableState'

const { route, prefs } = vi.hoisted(() => ({
  route: { query: {} as Record<string, string> },
  prefs: { load: vi.fn(), save: vi.fn() },
}))

vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ replace: vi.fn() }) }))
vi.mock('@/stores/members', () => ({ useMembersStore: () => ({ fetchMembers: vi.fn() }) }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => ({ activeDepartmentId: 7 }) }))
vi.mock('@/stores/listPreferences', () => ({ useListPreferencesStore: () => prefs }))

describe('useMembersTableState saved filters (UX-02.3)', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    route.query = {}
  })
  afterEach(() => vi.useRealTimers())

  it('applies the saved filters of the active department', async () => {
    prefs.load.mockResolvedValue({ status: 2, rows: 50, sortField: 'firstname', sortOrder: -1 })
    const state = useMembersTableState()
    await state.restoreSaved()
    expect(prefs.load).toHaveBeenCalledWith('members', 7)
    expect(state.filters.status).toBe(2)
    expect(state.lazyParams.rows).toBe(50)
    expect(state.lazyParams.sortOrder).toBe(-1)
  })

  it('keeps filters from a shared link instead of the saved ones', async () => {
    route.query = { status: '3' }
    const state = useMembersTableState()
    await state.restoreSaved()
    expect(prefs.load).not.toHaveBeenCalled()
    expect(state.filters.status).toBe(3)
  })

  it('saves filters without the search text', () => {
    const state = useMembersTableState()
    state.filters.search = 'Mia Beispiel'
    state.filters.group = 4
    state.onPage({ first: 0, rows: 20 })
    vi.advanceTimersByTime(900)
    expect(prefs.save).toHaveBeenCalledTimes(1)
    const [, department, data] = prefs.save.mock.calls[0]!
    expect(department).toBe(7)
    expect(data).toMatchObject({ group: 4, rows: 20 })
    expect(JSON.stringify(data)).not.toContain('Mia')
  })
})
