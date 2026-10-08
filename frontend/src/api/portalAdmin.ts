import apiClient from './index'

export type AccessKind = 'parent' | 'member'
export type AccessState = 'none' | 'invited' | 'expired' | 'active' | 'suspended'
export type InvitationState = 'open' | 'expired' | 'accepted' | 'revoked'

export interface Paginated<T> { count: number, next: string | null, previous: string | null, results: T[] }

export interface AccessRecord {
  kind: AccessKind
  id: number
  name: string
  email: string
  state: AccessState
  children: string[]
}

export interface PortalInvitation {
  id: number
  kind: AccessKind
  parent: number | null
  member: number | null
  person_name: string
  email: string
  state: InvitationState
  created_at: string
  created_by_name: string
  sent_at: string | null
  expires_at: string
  accepted_at: string | null
  revoked_at: string | null
}

export interface ChildAccess {
  member: number
  name: string
  access_ends_on: string | null
  extended_until: string | null
  ended: boolean
  ends_soon: boolean
}

export interface AccessDetail {
  kind: AccessKind
  id: number
  name: string
  email: string
  state: AccessState
  account: null | { username: string, is_active: boolean, last_login: string | null, linked_at: string }
  invitations: PortalInvitation[]
  children: ChildAccess[]
}

export interface EndingEntry {
  parent: number
  parent_name: string
  member: number
  name: string
  access_ends_on: string | null
  extended_until: string | null
  ended: boolean
  ends_soon: boolean
}

export interface BulkResult { parent: number, result: 'sent' | 'skipped', code?: string, detail?: string }

export interface RecordsQuery { kind: AccessKind, state?: AccessState | '', search?: string, limit?: number, offset?: number }
export interface Subject { parent?: number, member?: number }

export const portalAdminApi = {
  records(params: RecordsQuery) {
    return apiClient.get<Paginated<AccessRecord>>('/portal/access/records/', { params })
  },
  detail(subject: Subject) {
    return apiClient.get<AccessDetail>('/portal/access/', { params: subject })
  },
  invite(parent: number) {
    return apiClient.post<PortalInvitation>('/portal/invitations/', { parent })
  },
  resend(id: number) {
    return apiClient.post<PortalInvitation>(`/portal/invitations/${id}/resend/`)
  },
  revoke(id: number) {
    return apiClient.post<PortalInvitation>(`/portal/invitations/${id}/revoke/`)
  },
  invitations(params: { parent?: number, limit?: number, offset?: number } = {}) {
    return apiClient.get<Paginated<PortalInvitation>>('/portal/invitations/', { params })
  },
  bulkInvite(parents: number[]) {
    return apiClient.post<{ results: BulkResult[] }>('/portal/invitations/bulk/', { parents })
  },
  suspend(subject: Subject) { return apiClient.post<AccessDetail>('/portal/access/suspend/', subject) },
  resume(subject: Subject) { return apiClient.post<AccessDetail>('/portal/access/resume/', subject) },
  end(subject: Subject) { return apiClient.post<AccessDetail>('/portal/access/end/', subject) },
  extend(data: { parent: number, member: number, until: string, reason: string }) {
    return apiClient.post<AccessDetail>('/portal/access/extensions/', data)
  },
  ending() {
    return apiClient.get<EndingEntry[]>('/portal/access/ending/')
  },
}
