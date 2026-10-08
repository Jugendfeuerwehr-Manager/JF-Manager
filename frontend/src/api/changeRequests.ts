import apiClient from './index'
import type { ChangeRequest, ChangeTarget, DecidePayload, Review } from '@/types/changeRequests'

export const changeRequestsApi = {
  list() {
    return apiClient.get<{ results: ChangeRequest[] }>('/portal/change-requests/')
  },
  submit(target: ChangeTarget, fields: Record<string, string>) {
    return apiClient.post<ChangeRequest>('/portal/change-requests/', { target, fields })
  },
  withdraw(id: number) {
    return apiClient.post<ChangeRequest>(`/portal/change-requests/${id}/withdraw/`)
  },
  reviews(status: 'open' | 'decided') {
    return apiClient.get<{ results: Review[] }>('/portal/reviews/', { params: { status } })
  },
  decide(id: number, payload: DecidePayload) {
    return apiClient.post<Review>(`/portal/reviews/${id}/decide/`, payload)
  },
}
