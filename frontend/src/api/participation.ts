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
}

export type ConfigUpdate = Partial<Pick<ParticipationConfig,
  'mode' | 'portal_visible' | 'public_note' | 'registration_opens_at' | 'registration_closes_at'
  | 'cancellation_closes_at' | 'max_participants' | 'min_participants' | 'waitlist_mode'>>
  & { eligibility?: Rule | Record<string, never> | null, revision: number }

export interface RegistrationDetail {
  version: number
  reason_category: ReasonCategory
  reason_note: string | null
  source: 'portal_parent' | 'portal_member' | 'staff'
  late: boolean
  conflict: boolean
  conflict_reasons: string[]
  state_changed_at: string
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
  truncated: boolean
  members: RegistrationRow[]
}

export interface RegistrationInput {
  target: RegistrationTarget
  reason_category?: ReasonCategory
  reason_note?: string
  version?: number | null
  accept_waitlist?: boolean
}

export interface RuleValidation { summary: string, errors: RuleErrors, audience_notice: string | null }
export interface RulePreviewResult extends RuleValidation {
  total: number
  eligible: number
  excluded: Array<{ member_id: number, name: string, reasons: string[] }>
  /** Eligible people who meet a requirement through a higher qualification (E18). */
  substituted?: Array<{ member_id: number, name: string, notes: string[] }>
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
  validate(rule: Rule) {
    return apiClient.post<RuleValidation>('/participation/eligibility/validate/', { rule })
  },
  preview(rule: Rule, session: number) {
    return apiClient.post<RulePreviewResult>('/participation/eligibility/preview/', { rule, session })
  },
}
