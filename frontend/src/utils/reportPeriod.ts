/**
 * Periods for the attendance evaluation (UX-04.3); all dates are local calendar days.
 */

export type ReportRange = '3m' | '6m' | '12m' | 'year'

export const REPORT_RANGES: { value: ReportRange; label: string }[] = [
  { value: '3m', label: '3 Monate' },
  { value: '6m', label: '6 Monate' },
  { value: '12m', label: '12 Monate' },
  { value: 'year', label: 'Dieses Jahr' }
]

export function isReportRange(value: string): value is ReportRange {
  return REPORT_RANGES.some((range) => range.value === value)
}

function isoDate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

/** Whole months up to today, e.g. 3 months in October start on 1 August. */
export function reportPeriod(range: ReportRange, today = new Date()): { date_from: string; date_to: string } {
  const start =
    range === 'year'
      ? new Date(today.getFullYear(), 0, 1)
      : new Date(today.getFullYear(), today.getMonth() - (Number.parseInt(range, 10) - 1), 1)
  return { date_from: isoDate(start), date_to: isoDate(today) }
}

/** "2026-03" → "Mär 26" */
export function formatMonth(key: string, style: 'short' | 'long' = 'short'): string {
  const [year, month] = key.split('-').map(Number)
  const date = new Date(year ?? 1970, (month ?? 1) - 1, 1)
  return style === 'long'
    ? date.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' })
    : date.toLocaleDateString('de-DE', { month: 'short', year: '2-digit' }).replace('.', '')
}

export function formatRate(rate: number | null): string {
  return rate === null ? '–' : `${rate.toLocaleString('de-DE', { maximumFractionDigits: 0 })} %`
}
