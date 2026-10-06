import apiClient from './index'
import type { RoleTemplate, RoleTemplateComparison, RoleTemplateList } from '@/types/role-templates'

export const roleTemplatesApi = {
  list(offset = 0) {
    return apiClient.get<RoleTemplate[] | RoleTemplateList>('/admin/role-templates/', { params: { limit: 100, offset } })
  },
  compare(id: number) {
    return apiClient.get<RoleTemplateComparison>(`/admin/role-templates/${id}/compare/`, { params: {} })
  },
  update(id: number, data: { fingerprint: string; name?: string; description?: string; is_delegable?: boolean }) {
    return apiClient.patch<RoleTemplate>(`/admin/role-templates/${id}/`, data)
  },
  applyPermissions(id: number, data: { fingerprint: string; permissions: string[] }) {
    return apiClient.post<RoleTemplateComparison>(`/admin/role-templates/${id}/apply-permissions/`, data)
  },
  delegation(id: number, fingerprint: string, approved: boolean) {
    return apiClient.post<RoleTemplate>(`/admin/role-templates/${id}/delegation/`, { fingerprint, approved })
  },
  archive(id: number, fingerprint: string) {
    return apiClient.post<RoleTemplate>(`/admin/role-templates/${id}/archive/`, { fingerprint })
  },
  duplicate(id: number, data: { key: string; name: string; description?: string; is_delegable?: boolean; fingerprint: string }) {
    return apiClient.post<RoleTemplate>(`/admin/role-templates/${id}/duplicate/`, data)
  },
}

export async function listAssignableRoleGroups() {
  const groups: { id: number; name: string; scope: RoleTemplate['scope'] }[] = []
  let offset = 0
  while (true) {
    const { data } = await roleTemplatesApi.list(offset)
    const rows = Array.isArray(data) ? data : data.results
    for (const row of rows) if (row.group && !row.is_archived) groups.push({ id: row.group.id, name: row.name, scope: row.scope })
    if (Array.isArray(data) || !data.next || rows.length === 0) return groups
    offset += rows.length
  }
}
