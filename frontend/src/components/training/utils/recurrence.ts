import type { RecurrenceRule, TrainingSessionList } from '@/types/training'

export interface TrainingCalendarSession extends TrainingSessionList {
  occurrence_key: string
  occurrence_date: string
  is_series_occurrence: boolean
  is_recurring: boolean
}

function parseIsoDateLocal(isoDate: string): Date | null {
  const parts = isoDate.split('-').map((v) => Number(v))
  const year = parts[0]
  const month = parts[1]
  const day = parts[2]
  if (!year || !month || !day) return null
  return new Date(year, month - 1, day)
}

function formatIsoDateLocal(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function nextOccurrenceDate(date: Date, frequency: RecurrenceRule['frequency']): Date {
  if (frequency === 'WEEKLY') {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate() + 7)
  }
  if (frequency === 'BIWEEKLY') {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate() + 14)
  }

  const nextMonth = date.getMonth() + 1
  const nextYear = date.getFullYear() + Math.floor(nextMonth / 12)
  const normalizedMonth = nextMonth % 12
  const targetDay = date.getDate()
  const maxDay = new Date(nextYear, normalizedMonth + 1, 0).getDate()
  return new Date(nextYear, normalizedMonth, Math.min(targetDay, maxDay))
}

function isWithinRange(date: Date, start: Date, end: Date): boolean {
  return date >= start && date <= end
}

function getSeriesIndicator(session: TrainingSessionList, isSeriesOccurrence: boolean): boolean {
  return isSeriesOccurrence || session.series_parent !== null || session.recurrence_rule !== null
}

export function expandTrainingSessionsForRange(
  sessions: TrainingSessionList[],
  rangeStartIso: string,
  rangeEndIso: string,
): TrainingCalendarSession[] {
  const rangeStart = parseIsoDateLocal(rangeStartIso)
  const rangeEnd = parseIsoDateLocal(rangeEndIso)
  if (!rangeStart || !rangeEnd || rangeStart > rangeEnd) return []

  const childParentIds = new Set(
    sessions.filter((s) => s.series_parent !== null).map((s) => s.series_parent as number),
  )

  const expanded: TrainingCalendarSession[] = []
  const seen = new Set<string>()

  const addOccurrence = (session: TrainingSessionList, date: Date) => {
    const occurrenceDate = formatIsoDateLocal(date)
    const key = `${session.id}-${occurrenceDate}`
    if (seen.has(key)) return
    seen.add(key)
    expanded.push({
      ...session,
      occurrence_key: key,
      occurrence_date: occurrenceDate,
      is_series_occurrence: occurrenceDate !== session.date,
      is_recurring: getSeriesIndicator(session, occurrenceDate !== session.date),
    })
  }

  for (const session of sessions) {
    const baseDate = parseIsoDateLocal(session.date)
    if (!baseDate) continue

    if (isWithinRange(baseDate, rangeStart, rangeEnd)) {
      addOccurrence(session, baseDate)
    }

    const recurrence = session.recurrence_rule
    if (!recurrence || session.series_parent !== null || childParentIds.has(session.id)) {
      continue
    }

    const recurrenceEnd = parseIsoDateLocal(recurrence.end_date)
    if (!recurrenceEnd || recurrenceEnd <= baseDate) {
      continue
    }

    let cursor = baseDate
    const hardEnd = recurrenceEnd < rangeEnd ? recurrenceEnd : rangeEnd
    while (cursor < hardEnd) {
      cursor = nextOccurrenceDate(cursor, recurrence.frequency)
      if (cursor > hardEnd) break
      if (cursor < rangeStart) continue
      addOccurrence(session, cursor)
    }
  }

  return expanded.sort((a, b) => {
    const byDate = a.occurrence_date.localeCompare(b.occurrence_date)
    if (byDate !== 0) return byDate
    const byStart = a.start_time.localeCompare(b.start_time)
    if (byStart !== 0) return byStart
    return a.title.localeCompare(b.title)
  })
}
