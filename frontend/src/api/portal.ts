import apiClient from './index'

export interface PortalPerson {
  id: number
  relation: 'self' | 'child'
  first_name: string
  last_name: string
  /** Only present when the birthday is released. */
  age?: number
}

export interface PortalParentContact {
  first_name: string, last_name: string, street: string, zip_code: string, city: string
  phone: string, mobile: string, email: string, email2: string
}

export interface PortalMe {
  account: { first_name: string, last_name: string, email: string }
  people: PortalPerson[]
  parent?: PortalParentContact | null
}

export interface PortalPersonData {
  id: number
  relation: 'self' | 'child'
  categories: string[]
  contact: { first_name: string, last_name: string, street: string, zip_code: string, city: string, phone: string, mobile: string, email: string }
  birthday?: string
  age?: number
  group?: { group: string | null, departments: string[] }
  membership?: { status: string, joined: string | null }
  identity?: { card_number: string }
  swimming?: { can_swim: boolean }
  qualifications?: { type: string, acquired: string | null, expires: string | null, valid: boolean }[]
  special_tasks?: { task: string, start: string | null, end: string | null }[]
  equipment?: { item: string, variant: string, quantity: number }[]
  other_parents?: { name: string, phone: string, mobile: string }[]
}

export interface InvitationInfo {
  email: string
  kind: 'parent' | 'member'
  expires_at: string
}

export interface AcceptInvitationPayload {
  token: string
  password: string
  password_confirm: string
  privacy_accepted: boolean
}

export type PortalRegistrationState =
  'expected' | 'no_response' | 'registered' | 'waitlisted' | 'applied' | 'assigned' | 'not_selected' | 'cancelled'
export type PortalMode = 'opt_out' | 'opt_in' | 'assignment'
export type PortalReason = 'krankheit' | 'schule_beruf' | 'urlaub' | 'familie' | 'sonstiges'
export type PortalTarget = 'registered' | 'cancelled' | 'applied' | 'withdrawn'

export interface PortalBlocked { code: string, detail: string, reasons: string[] }

export interface PortalSessionItem {
  id: number
  title: string
  date: string
  start_time: string | null
  end_time: string | null
  place: string
  session_status: 'published' | 'cancelled'
  mode: PortalMode
  public_note: string
  state: PortalRegistrationState
  waitlist_position: number | null
  reason_category: PortalReason | ''
  version: number
  late: boolean
  /** Requirement lapsed after registering (PART-03.5); neutral, no reasons. */
  conflict?: boolean
  deadlines: { registration_opens_at: string | null, registration_closes_at: string | null, cancellation_closes_at: string | null }
  limited: boolean
  free_places: number | null
  /** Optional: only when the server reports the capacity. */
  max_participants?: number | null
  eligibility: { ok: boolean, reasons: string[], audience_notice: string | null }
  may_register: boolean
  may_cancel: boolean
  register_blocked: PortalBlocked | null
  cancel_blocked: PortalBlocked | null
}

export interface PortalRegistrationPayload {
  target: PortalTarget
  reason_category?: PortalReason | ''
  reason_note?: string
  version?: number
  accept_waitlist?: boolean
}

export interface PortalAbsencePayload {
  person: number
  from: string
  to: string
  reason_category?: PortalReason | ''
  reason_note?: string
}

export interface PortalAbsencePreviewRow {
  id: number
  title: string
  date: string
  start_time: string | null
  end_time: string | null
  place: string
  state: string
  action: 'cancel' | 'skip'
  skip: { code: string, detail: string } | null
}

export interface PortalAbsenceResult {
  person: number
  cancelled: { id: number, title: string, date: string, start_time: string | null }[]
  skipped: { id: number, title: string, date: string, start_time: string | null, code: string, detail: string }[]
}

export interface PortalNotice {
  id: number
  kind: string
  category?: string
  type?: string
  title: string
  count?: number
  link: string
  updated_at: string
  read: boolean
}

export const portalApi = {
  notifications() {
    return apiClient.get<{ results: PortalNotice[], unread: number }>('/portal/notifications/')
  },
  markNotificationRead(id: number) {
    return apiClient.post(`/portal/notifications/${id}/read/`)
  },
  sessions(person: number, params?: { from?: string, to?: string }) {
    return apiClient.get<{ person: number, sessions: PortalSessionItem[] }>('/portal/sessions/', { params: { person, ...params } })
  },
  setRegistration(sessionId: number, memberId: number, data: PortalRegistrationPayload) {
    return apiClient.put<PortalSessionItem>(`/portal/sessions/${sessionId}/registrations/${memberId}/`, data)
  },
  previewAbsence(data: PortalAbsencePayload) {
    return apiClient.post<{ person: number, sessions: PortalAbsencePreviewRow[], will_cancel: number, skipped: number }>('/portal/absences/preview/', data)
  },
  createAbsence(data: PortalAbsencePayload) {
    return apiClient.post<PortalAbsenceResult>('/portal/absences/', data)
  },
  invitationInfo(token: string) {
    return apiClient.get<InvitationInfo>('/portal/invitations/accept/', { params: { token } })
  },
  acceptInvitation(data: AcceptInvitationPayload) {
    return apiClient.post<{ username: string }>('/portal/invitations/accept/', data)
  },
  person(id: number) {
    return apiClient.get<PortalPersonData>(`/portal/people/${id}/`)
  },
  me() {
    return apiClient.get<PortalMe>('/portal/me/')
  },
}
