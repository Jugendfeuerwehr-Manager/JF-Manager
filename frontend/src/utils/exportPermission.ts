import type { UserInfo } from '@/types/api'

export function canExport(user: UserInfo | null, codename: string, department: number | null): boolean {
  if (!user) return false
  if (user.is_superuser) return true
  const contains = (permissions: string[]) => permissions.includes(codename) || permissions.includes(`members.${codename}`)
  if (contains(user.permissions)) return true
  return user.department_roles.some(role => (department === null || role.department_id === department) && contains(role.permissions))
}
