import { describe, expect, it } from 'vitest'
import type { TrainingSessionList } from '@/types/training'
import { calendarSessionsForRange } from '../recurrence'

function makeSession(overrides: Partial<TrainingSessionList> = {}): TrainingSessionList {
  return {
    status: 'draft', requires_service_confirmation: false, can_manage_plan: true,
    id: 1,
    title: 'Dienstabend',
    date: '2026-05-01',
    start_time: '18:00',
    end_time: '20:00',
    location: 'Gerätehaus',
    group_count: 0,
    groups: [],
    block_count: 0,
    department: null,
    linked_service_id: null,
    linked_service_start: null,
    series_parent: null,
    series_uuid: null,
    original_date: null,
    recurrence_rule: null,
    ...overrides,
  }
}

describe('calendarSessionsForRange', () => {
  it('never invents virtual occurrences that would open the parent plan', () => {
    const root = makeSession({
      id: 7,
      date: '2026-05-01',
      recurrence_rule: { frequency: 'WEEKLY', end_date: '2026-05-29' },
    })
    const entries = calendarSessionsForRange([root], '2026-05-01', '2026-05-31')
    expect(entries.map((s) => `${s.id}@${s.occurrence_date}`)).toEqual(['7@2026-05-01'])
    expect(entries[0]?.is_recurring).toBe(true)
  })

  it('shows each stored occurrence with its own id, including moved ones', () => {
    const series = 'b4b8c2e2-5f7f-4a5f-9a54-6f5d2a1c0b11'
    const root = makeSession({ id: 1, series_uuid: series, recurrence_rule: { frequency: 'WEEKLY', end_date: '2026-05-31' } })
    const moved = makeSession({ id: 3, date: '2026-05-09', original_date: '2026-05-08', series_parent: 1, series_uuid: series })
    const child = makeSession({ id: 2, date: '2026-05-15', original_date: '2026-05-15', series_parent: 1, series_uuid: series })
    const single = makeSession({ id: 9, date: '2026-05-15', start_time: '10:00' })
    const entries = calendarSessionsForRange([child, single, root, moved], '2026-05-01', '2026-05-31')
    expect(entries.map((s) => `${s.id}@${s.occurrence_date}`)).toEqual(['1@2026-05-01', '3@2026-05-09', '9@2026-05-15', '2@2026-05-15'])
    expect(entries.map((s) => s.is_recurring)).toEqual([true, true, false, true])
  })

  it('filters by range and rejects inverted ranges', () => {
    const sessions = [makeSession({ id: 1, date: '2026-04-30' }), makeSession({ id: 2, date: '2026-05-02' })]
    expect(calendarSessionsForRange(sessions, '2026-05-01', '2026-05-31').map((s) => s.id)).toEqual([2])
    expect(calendarSessionsForRange(sessions, '2026-06-01', '2026-05-01')).toEqual([])
  })
})
