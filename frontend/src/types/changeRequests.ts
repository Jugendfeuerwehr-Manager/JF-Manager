export type ChangeRequestStatus = 'open' | 'partial' | 'applied' | 'rejected' | 'withdrawn'
export type ChangeDecision = 'apply' | 'reject'
export type ChangeTarget = { kind: 'member', id: number } | { kind: 'parent' }

export interface ChangeRequestField {
  field: string
  label: string
  old: string
  new: string
  decision?: ChangeDecision
}

export interface ChangeRequest {
  id: number
  kind: 'member' | 'parent'
  target_id: number
  person_name: string
  status: ChangeRequestStatus
  status_label: string
  version: number
  fields: ChangeRequestField[]
  decision_note: string
  created_at: string
  updated_at: string
  decided_at: string | null
}

export interface ReviewField extends ChangeRequestField {
  current: string
  conflict: boolean
}

export interface Review extends Omit<ChangeRequest, 'fields'> {
  fields: ReviewField[]
  requested_by: string
  /** Four-eyes rule: the viewer may not decide this request. */
  own: boolean
}

export interface ChangeRequestErrorBody {
  detail?: string
  code?: string
  fields?: Record<string, string>
}

export interface DecidePayload {
  version: number
  decisions: Record<string, ChangeDecision>
  confirm_conflicts: string[]
  note?: string
}
