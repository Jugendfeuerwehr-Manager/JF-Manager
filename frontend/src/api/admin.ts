import apiClient from './index'
import type {
  AdminUser,
  AdminUserDetail,
  AdminUserWrite,
  AuthGroup,
  AuthGroupDetail,
  AuthGroupWrite,
  PaginatedAdminUsers,
  PaginatedAuthGroups,
  PaginatedPermissions,
} from '@/types/admin'

export interface AdminUserListParams {
  limit?: number
  offset?: number
  search?: string
  ordering?: string
  is_active?: boolean
  is_staff?: boolean
  is_superuser?: boolean
}

export const adminUsersApi = {
  list(params?: AdminUserListParams) {
    return apiClient.get<PaginatedAdminUsers>('/admin/users/', { params })
  },
  get(id: number) {
    return apiClient.get<AdminUserDetail>(`/admin/users/${id}/`)
  },
  create(data: AdminUserWrite) {
    return apiClient.post<AdminUser>('/admin/users/', data)
  },
  update(id: number, data: Partial<AdminUserWrite>) {
    return apiClient.patch<AdminUser>(`/admin/users/${id}/`, data)
  },
  delete(id: number) {
    return apiClient.delete(`/admin/users/${id}/`)
  },
  setGroups(id: number, groupIds: number[]) {
    return apiClient.patch<AdminUserDetail>(`/admin/users/${id}/set-groups/`, {
      group_ids: groupIds,
    })
  },
}

export const adminGroupsApi = {
  list(params?: { search?: string; ordering?: string; limit?: number; offset?: number }) {
    return apiClient.get<PaginatedAuthGroups>('/admin/groups/', { params })
  },
  get(id: number) {
    return apiClient.get<AuthGroupDetail>(`/admin/groups/${id}/`)
  },
  create(data: AuthGroupWrite) {
    return apiClient.post<AuthGroup>('/admin/groups/', data)
  },
  update(id: number, data: Partial<AuthGroupWrite>) {
    return apiClient.patch<AuthGroup>(`/admin/groups/${id}/`, data)
  },
  delete(id: number) {
    return apiClient.delete(`/admin/groups/${id}/`)
  },
}

export const adminPermissionsApi = {
  list(params?: { search?: string; limit?: number; offset?: number }) {
    return apiClient.get<PaginatedPermissions>('/admin/permissions/', { params })
  },
}
