import apiClient from './index'

export type ParticipationMode = 'opt_out' | 'opt_in' | 'assignment'
export type WaitlistMode = 'auto' | 'manual'
export type RegistrationState = 'registered' | 'waitlisted' | 'applied' | 'assigned' | 'not_selected' | 'cancelled'
export type DisplayState = RegistrationState | 'expected' | 'no_response'
export type RegistrationTarget = 'registered' | 'cancelled' | 'applied' | 'withdrawn'
export type ReasonCategory = '' | 'krankheit' | 'schule_beruf' | 'urlaub' | 'familie' | 'sonstiges'

// ── Rule language v1 (backend/participation/rules.py) ─────────────────────
export type RuleMatch = 'all' | 'any'
export type HasOp = 'has_any' | 'has_all' | 'has_none'
export type ValueKind = 'qualification' | 'special_task' | 'gender' | 'group' | 'status' | 'department'
export type RuleKind = ValueKind | 'age'
export type AgeOp = 'min' | 'max' | 'between'

export interface ValueCondition { kind: ValueKind, op: HasOp | 'in', values: Array<number | string> }
export interface AgeCondition { kind: 'age', op: AgeOp, min?: number, max?: number }
export type RuleCondition = ValueCondition | AgeCondition
export interface RuleGroup { match: RuleMatch, rules: RuleCondition[] }
export interface Rule { v: 1, match: RuleMatch, rules: Array<RuleCondition | RuleGroup> }

export type RuleErrors = Record<string, string>

// ── Positions (PART-04) ───────────────────────────────────────────────────
export interface SlotConfig {
  id: number
  label: string
  min: number
  max: number
  rule: Rule | Record<string, never>
  rule_summary: string | null
  position: number
  seated: number
}

export interface SlotInput {
  id?: number | null
  label: string
  min: number
  max: number
  rule: Rule | Record<string, never>
}

export interface StaffingRow { id: number, label: string, min: number, max: number, seated: number, free: number, missing: number }
export interface Staffing {
  met: boolean
  required: number
  fulfilled: number
  missing: Array<{ label: string, count: number }>
  text: string
  slots: StaffingRow[]
}

export interface ParticipationConfig {
  session: number
  revision: number
  mode: ParticipationMode
  portal_visible: boolean
  public_note: string
  registration_opens_at: string | null
  registration_closes_at: string | null
  cancellation_closes_at: string | null
  max_participants: number | null
  min_participants: number | null
  waitlist_mode: WaitlistMode
  eligibility: Rule | Record<string, never> | null
  effective: {
    start: string
    registration_opens_at: string | null
    registration_closes_at: string
    cancellation_closes_at: string
  }
  defaults: { mode: ParticipationMode, registration_offset_h: number, cancellation_offset_h: number, waitlist_mode: WaitlistMode }
  eligibility_summary: string | null
  audience_notice: string | null
  extra_places: number | null
  slots: SlotConfig[]
  capacity: number | null
  staffing: Staffing | null
}

export type ConfigUpdate = Partial<Pick<ParticipationConfig,
  'mode' | 'portal_visible' | 'public_note' | 'registration_opens_at' | 'registration_closes_at'
  | 'cancellation_closes_at' | 'max_participants' | 'min_participants' | 'waitlist_mode'>>
  & { eligibility?: Rule | Record<string, never> | null, revision: number, extra_places?: number | null, slots?: SlotInput[] }

export interface RegistrationDetail {
  version: number
  reason_category: ReasonCategory
  reason_note: string | null
  source: 'portal_parent' | 'portal_member' | 'staff'
  late: boolean
  conflict: boolean
  conflict_reasons: string[]
  state_changed_at: string
  slot: number | null
  preferred_slot: number | null
}

export interface RegistrationRow {
  member_id: number
  name: string
  lastname: string
  group_id: number | null
  in_target: boolean
  state: DisplayState
  waitlist_position: number | null
  eligibility: { ok: boolean, reasons: string[] }
  registration: RegistrationDetail | null
}

export interface RegistrationCounts extends Record<string, number | null> {
  seated: number
  conflicts: number
  late: number
  max_participants: number | null
  min_participants: number | null
  free: number | null
}

export interface RegistrationOverview {
  session: { id: number, title: string, date: string, start_time: string, status: string }
  mode: ParticipationMode
  revision: number
  deadlines: { registration_opens_at: string | null, registration_closes_at: string, cancellation_closes_at: string }
  counts: RegistrationCounts
  slots: SlotConfig[]
  extra_places: number | null
  staffing: Staffing | null
  truncated: boolean
  members: RegistrationRow[]
}

export interface RegistrationInput {
  target: RegistrationTarget
  reason_category?: ReasonCategory
  reason_note?: string
  version?: number | null
  accept_waitlist?: boolean
  slot?: number | null
}

export interface RuleValidation { summary: string, errors: RuleErrors, audience_notice: string | null }
export interface RulePreviewResult extends RuleValidation {
  total: number
  eligible: number
  excluded: Array<{ member_id: number, name: string, reasons: string[] }>
  /** Eligible people who meet a requirement through a higher qualification (E18). */
  substituted?: Array<{ member_id: number, name: string, notes: string[] }>
}

// ── Assignment board (PART-04.4) ──────────────────────────────────────────
/** Draft target: a position id or "extra" (place without position). */
export type DraftTarget = number | 'extra'

export interface BoardApplicant {
  member_id: number
  name: string
  lastname: string
  state: 'applied' | 'assigned' | 'not_selected'
  version: number
  applied_at: string
  preferred_slot: number | null
  general_ok: boolean
  general_reasons: string[]
  fits: number[]
  reasons: Record<string, string[]>
  notes: string[]
  qualifications: string[]
  recent_assignments: number
  draft: DraftTarget | null
  published: DraftTarget | null
  conflict: boolean
}

export interface BoardSlot { id: number, label: string, min: number, max: number, drafted: number }

export interface AssignmentBoard {
  session: number
  mode: ParticipationMode
  revision: number
  published_at: string | null
  keep_open: boolean
  dirty: boolean
  slots: BoardSlot[]
  extra_places: number | null
  extra_drafted: number
  staffing: Staffing | null
  applicants: BoardApplicant[]
  draft: Record<string, DraftTarget>
}

export const participationApi = {
  config(sessionId: number) {
    return apiClient.get<ParticipationConfig>(`/participation/sessions/${sessionId}/config/`)
  },
  saveConfig(sessionId: number, body: ConfigUpdate) {
    return apiClient.put<ParticipationConfig>(`/participation/sessions/${sessionId}/config/`, body)
  },
  registrations(sessionId: number) {
    return apiClient.get<RegistrationOverview>(`/participation/sessions/${sessionId}/registrations/`)
  },
  setRegistration(sessionId: number, memberId: number, body: RegistrationInput) {
    return apiClient.put<RegistrationRow & { changed: boolean }>(
      `/participation/sessions/${sessionId}/registrations/${memberId}/`, body)
  },
  assignment(sessionId: number) {
    return apiClient.get<AssignmentBoard>(`/participation/sessions/${sessionId}/assignment/`)
  },
  saveAssignment(sessionId: number, body: { revision: number, draft: Record<string, DraftTarget> }) {
    return apiClient.put<AssignmentBoard>(`/participation/sessions/${sessionId}/assignment/`, body)
  },
  publishAssignment(sessionId: number, body: { revision: number, keep_open: boolean }) {
    return apiClient.post<AssignmentBoard>(`/participation/sessions/${sessionId}/assignment/publish/`, body)
  },
  validate(rule: Rule) {
    return apiClient.post<RuleValidation>('/participation/eligibility/validate/', { rule })
  },
  preview(rule: Rule, session: number) {
    return apiClient.post<RulePreviewResult>('/participation/eligibility/preview/', { rule, session })
  },
}
