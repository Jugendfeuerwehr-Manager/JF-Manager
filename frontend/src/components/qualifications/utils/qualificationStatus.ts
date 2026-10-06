import type { StatusSeverity } from '@/components/common/StatusBadge.vue'
import type { Qualification } from '@/types/qualifications'

export interface QualificationStatus {
  label: string
  severity: StatusSeverity
}

const DAY_MS = 24 * 60 * 60 * 1000

/** Whole days from today until the expiry date; negative once expired, null without expiry. */
export function daysUntilExpiry(qualification: Pick<Qualification, 'date_expires'>, today = new Date()): number | null {
  if (!qualification.date_expires) return null
  const start = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate())
  const [y, m, d] = qualification.date_expires.split('-').map(Number)
  return Math.round((Date.UTC(y!, m! - 1, d!) - start) / DAY_MS)
}

/** One wording for validity across table, cards and detail views. */
export function qualificationStatus(qualification: Qualification, today = new Date()): QualificationStatus {
  const days = daysUntilExpiry(qualification, today)
  if (qualification.is_expired || (days !== null && days < 0)) return { label: 'Abgelaufen', severity: 'danger' }
  if (days === null) return { label: 'Unbefristet gültig', severity: 'success' }
  if (days === 0) return { label: 'Läuft heute ab', severity: 'warning' }
  if (days <= 90) return { label: `Läuft in ${days} ${days === 1 ? 'Tag' : 'Tagen'} ab`, severity: days <= 30 ? 'warning' : 'info' }
  return { label: 'Gültig', severity: 'success' }
}

export function formatDate(value: string | null): string {
  if (!value) return '–'
  const [y, m, d] = value.split('-')
  return `${d}.${m}.${y}`
}
