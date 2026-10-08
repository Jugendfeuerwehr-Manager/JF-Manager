import apiClient from './index'

export interface PortalPerson {
  id: number
  relation: 'self' | 'child'
  first_name: string
  last_name: string
}

export interface PortalMe {
  account: { first_name: string, last_name: string, email: string }
  people: PortalPerson[]
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
  me() {
    return apiClient.get<PortalMe>('/portal/me/')
  },
}
