/**
 * TypeScript types for membership movements (joins, stage changes, exits).
 */
import type { PaginatedResponse } from './common'
import type { StatusCategory } from './members'

export type JoinKind = 'joined_new' | 'joined_other_org' | 'joined_from_kf'
export type ExitKind = 'exit_ea' | 'exit_other'
export type MovementKind = JoinKind | ExitKind | 'stage_changed'

export type ExitReason =
  | 'relocation'
  | 'lost_interest'
  | 'school'
  | 'vocational_training'
  | 'expelled'
  | 'no_transfer_ea'

export const STATUS_CATEGORY_LABELS: Record<StatusCategory, string> = {
  applicant: 'Antrag',
  trial: 'Probezeit / Anwärter',
  active: 'Aktiv',
  passive: 'Passiv',
  left: 'Ausgetreten',
  transferred: 'Übergetreten'
}

export const EXIT_KIND_LABELS: Record<ExitKind, string> = {
  exit_ea: 'Übertritt in die Einsatzabteilung',
  exit_other: 'Sonstiger Abgang'
}

export const EXIT_REASON_LABELS: Record<ExitReason, string> = {
  relocation: 'Wohnortwechsel',
  lost_interest: 'Interesse an JF verloren',
  school: 'Belastung durch Schule',
  vocational_training: 'Berufsausbildung',
  expelled: 'Verweis bzw. Ausschluss aus der JF',
  no_transfer_ea: 'Möchte keine Übernahme in EA'
}

export interface MembershipEvent {
  id: number
  member: number
  department: number | null
  department_name: string | null
  date: string
  kind: MovementKind
  kind_label: string
  exit_reason: ExitReason | ''
  exit_reason_label: string
  from_status_name: string | null
  to_status_name: string | null
  note: string
  /** Who recorded the movement; null for imported or older entries. */
  created_by_name: string | null
  created_at: string
}

export interface MembershipEventCorrection {
  date?: string
  kind?: MovementKind
  exit_reason?: ExitReason | ''
  note?: string
}

export interface MembershipEventListParams {
  member?: number
  department?: number
  kind?: MovementKind
  date__year?: number
  limit?: number
  offset?: number
}

export type MembershipEventPage = PaginatedResponse<MembershipEvent>

export interface LeavePayload {
  /** null withdraws the leave */
  left_at: string | null
  status_id?: number
  kind?: ExitKind
  exit_reason?: ExitReason | ''
}

// ── DJF annual report ───────────────────────────────────────────────────────

export interface GenderCounts {
  m: number
  w: number
  d: number
  total: number
}

export interface ReportRow extends GenderCounts {
  key: string
  label: string
}

export interface ReportCheck {
  rule: string
  ok: boolean
  message: string
}

export interface ReportWarning {
  member: number
  name: string
  message: string
}

export interface ReportManual {
  supervisors?: GenderCounts
  activities?: { label: string; value: number }[]
}

export interface AnnualReportData {
  year: number
  reference_date: string
  organisation: { name: string; djf_org_id: string; org_kind: 'JF' | 'KF'; founded_on: string | null }
  members: GenderCounts
  previous: GenderCounts & { source: 'snapshot' | 'computed' }
  movements: ReportRow[]
  exit_reasons: { key: ExitReason; label: string; total: number }[]
  age: ReportRow[]
  checks: ReportCheck[]
  ok: boolean
  warnings: ReportWarning[]
  approximated_ages: number
  suggestions: { supervisors: number; services: number }
  manual: ReportManual
}

export interface AnnualReportResponse {
  state: 'draft' | 'final'
  finalized_at?: string | null
  data: AnnualReportData
}

export interface StatisticsProfile {
  id: number
  department: number
  djf_org_id: string
  org_kind: 'JF' | 'KF'
  founded_on: string | null
  include_status_categories: ('trial' | 'active' | 'passive')[]
}
