import { describe, expect, it } from 'vitest'
import type { TrainingSessionList } from '@/types/training'
import { expandTrainingSessionsForRange } from '../recurrence'

function makeSession(overrides: Partial<TrainingSessionList> = {}): TrainingSessionList {
  return {
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
    recurrence_rule: null,
    ...overrides,
  }
}

describe('expandTrainingSessionsForRange', () => {
  it('expands weekly recurring sessions within range without duplicating IDs', () => {
    const sessions: TrainingSessionList[] = [
      makeSession({
        id: 7,
        recurrence_rule: {
          frequency: 'WEEKLY',
          end_date: '2026-05-22',
        },
      }),
    ]

    const expanded = expandTrainingSessionsForRange(sessions, '2026-05-01', '2026-05-31')

    expect(expanded.map((s) => s.occurrence_date)).toEqual([
      '2026-05-01',
      '2026-05-08',
      '2026-05-15',
      '2026-05-22',
    ])
    expect(new Set(expanded.map((s) => s.id))).toEqual(new Set([7]))
    expect(expanded[0]?.is_series_occurrence).toBe(false)
    expect(expanded[1]?.is_series_occurrence).toBe(true)
    expect(expanded.every((s) => s.is_recurring)).toBe(true)
  })

  it('does not expand recurrence when generated children exist', () => {
    const parent = makeSession({
      id: 10,
      recurrence_rule: {
        frequency: 'WEEKLY',
        end_date: '2026-05-22',
      },
    })
    const child = makeSession({
      id: 11,
      date: '2026-05-08',
      series_parent: 10,
      recurrence_rule: null,
    })

    const expanded = expandTrainingSessionsForRange([parent, child], '2026-05-01', '2026-05-31')

    expect(expanded.map((s) => `${s.id}@${s.occurrence_date}`)).toEqual([
      '10@2026-05-01',
      '11@2026-05-08',
    ])
    expect(expanded[1]?.is_recurring).toBe(true)
  })
})
