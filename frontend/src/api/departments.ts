/**
 * API client for department management endpoints.
 */
import apiClient from './index'
import type { PaginatedResponse } from '@/types/common'
import type {
  Department,
  DepartmentCreate,
  DepartmentUpdate,
  UserDepartmentRole,
  UserDepartmentRoleCreate,
  UserDepartmentRoleUpdate,
} from '@/types/departments'

export const departmentsApi = {
  list() {
    return apiClient.get<PaginatedResponse<Department>>('/departments/')
  },

  get(id: number) {
    return apiClient.get<Department>(`/departments/${id}/`)
  },

  create(data: DepartmentCreate) {
    return apiClient.post<Department>('/departments/', data)
  },

  update(id: number, data: DepartmentUpdate) {
    return apiClient.patch<Department>(`/departments/${id}/`, data)
  },

  replace(id: number, data: DepartmentCreate) {
    return apiClient.put<Department>(`/departments/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/departments/${id}/`)
  },
}

export const departmentRolesApi = {
  list(params?: { user?: number; department?: number }) {
    return apiClient.get<PaginatedResponse<UserDepartmentRole>>('/admin/department-roles/', {
      params,
    })
  },

  create(data: UserDepartmentRoleCreate) {
    return apiClient.post<UserDepartmentRole>('/admin/department-roles/', data)
  },

  update(id: number, data: UserDepartmentRoleUpdate) {
    return apiClient.patch<UserDepartmentRole>(`/admin/department-roles/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/admin/department-roles/${id}/`)
  },
}
