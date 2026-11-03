/**
 * Additional member fields API – only HTTP, no logic.
 */
import apiClient from './index'
import type { PaginatedResponse } from '@/types/common'
import type { MemberFieldDefinition, MemberFieldDefinitionInput } from '@/types/members'

export const memberFieldsApi = {
  list: () => apiClient.get<PaginatedResponse<MemberFieldDefinition>>('/member-fields/', { params: { limit: 500 } }),
  create: (data: MemberFieldDefinitionInput) => apiClient.post<MemberFieldDefinition>('/member-fields/', data),
  update: (id: number, data: Partial<MemberFieldDefinitionInput>) =>
    apiClient.patch<MemberFieldDefinition>(`/member-fields/${id}/`, data),
  remove: (id: number) => apiClient.delete(`/member-fields/${id}/`)
}
