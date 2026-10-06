import apiClient from './index'
import type { RoleAssignmentInput, RoleAssignmentOptions, RoleAssignmentPreview, RoleExplanation } from '@/types/role-assignments'

export const roleAssignmentsApi = {
  options: () => apiClient.get<RoleAssignmentOptions>('/role-assignments/options/'),
  explain: (user?: number) => apiClient.get<{ roles: RoleExplanation[] }>('/role-assignments/explain/', { params: { user } }),
  preview: (data: RoleAssignmentInput) => apiClient.post<RoleAssignmentPreview>('/role-assignments/preview/', data),
  apply: (data: RoleAssignmentInput & { fingerprint: string }) => apiClient.post<{ saved: boolean; roles: RoleExplanation[] }>('/role-assignments/apply/', data),
}
