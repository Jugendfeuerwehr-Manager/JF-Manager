import apiClient from './index'
import type { PaginatedResponse } from '@/types/common'
import type { MemberList } from '@/types/lists'
import type {
  PendingLegacyList,
  ResolveLegacyListInput,
  ResolveLegacyListResult,
} from '@/types/legacy-list-resolution'

export const legacyListResolutionApi = {
  pending() {
    return apiClient.get<PendingLegacyList[]>('/member-lists/pending-resolution/', { params: {} })
  },

  targets(departmentId: number, page = 1) {
    return apiClient.get<PaginatedResponse<MemberList>>('/member-lists/', { params: { department: departmentId, page } })
  },

  get(sourceId: number) {
    return apiClient.get<PendingLegacyList>(`/member-lists/${sourceId}/resolve-legacy/`, { params: {} })
  },

  resolve(sourceId: number, data: ResolveLegacyListInput) {
    return apiClient.post<ResolveLegacyListResult>(`/member-lists/${sourceId}/resolve-legacy/`, data)
  },
}
