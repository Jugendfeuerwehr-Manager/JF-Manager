import type { TrainingSessionList } from '@/types/training'

export interface TrainingCalendarSession extends TrainingSessionList {
  occurrence_key: string
  occurrence_date: string
  is_recurring: boolean
}

export function isSeriesSession(session: TrainingSessionList): boolean {
  return session.series_uuid !== null || session.series_parent !== null || session.recurrence_rule !== null
}

/**
 * Only stored sessions are shown. Missing series occurrences are added through
 * the explicit series preview, so every entry opens its own plan.
 */
export function calendarSessionsForRange(
  sessions: TrainingSessionList[],
  rangeStartIso: string,
  rangeEndIso: string,
): TrainingCalendarSession[] {
  if (!rangeStartIso || !rangeEndIso || rangeStartIso > rangeEndIso) return []
  return sessions
    .filter((session) => session.date >= rangeStartIso && session.date <= rangeEndIso)
    .map((session) => ({
      ...session,
      occurrence_key: String(session.id),
      occurrence_date: session.date,
      is_recurring: isSeriesSession(session),
    }))
    .sort(
      (a, b) =>
        a.date.localeCompare(b.date) || a.start_time.localeCompare(b.start_time) || a.title.localeCompare(b.title),
    )
}
