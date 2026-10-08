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

export const portalApi = {
  me() {
    return apiClient.get<PortalMe>('/portal/me/')
  },
}
