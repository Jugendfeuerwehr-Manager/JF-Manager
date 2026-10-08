import { describe, expect, it } from 'vitest'
import { formatRate, isReportRange, reportPeriod } from '../reportPeriod'

describe('reportPeriod', () => {
  const today = new Date(2026, 9, 7)

  it('covers whole months up to today', () => {
    expect(reportPeriod('3m', today)).toEqual({ date_from: '2026-08-01', date_to: '2026-10-07' })
    expect(reportPeriod('12m', today)).toEqual({ date_from: '2025-11-01', date_to: '2026-10-07' })
    expect(reportPeriod('year', today)).toEqual({ date_from: '2026-01-01', date_to: '2026-10-07' })
  })

  it('crosses the year boundary', () => {
    expect(reportPeriod('6m', new Date(2026, 1, 15))).toEqual({ date_from: '2025-09-01', date_to: '2026-02-15' })
  })

  it('validates URL values and formats rates', () => {
    expect(isReportRange('6m')).toBe(true)
    expect(isReportRange('2y')).toBe(false)
    expect(formatRate(66.7)).toBe('67 %')
    expect(formatRate(null)).toBe('–')
  })
})
