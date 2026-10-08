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

export const portalApi = {
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
