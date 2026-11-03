/**
 * Membership movements API – only HTTP, no logic.
 */
import apiClient from './index'
import type {
  MembershipEvent,
  MembershipEventCorrection,
  MembershipEventListParams,
  MembershipEventPage
} from '@/types/membership'

export const membershipApi = {
  listEvents: (params?: MembershipEventListParams) =>
    apiClient.get<MembershipEventPage>('/membership/events/', { params }),

  correctEvent: (id: number, data: MembershipEventCorrection) =>
    apiClient.patch<MembershipEvent>(`/membership/events/${id}/`, data)
}
