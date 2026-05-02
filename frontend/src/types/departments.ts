/**
 * TypeScript types for multi-department support.
 */

// ── Department ───────────────────────────────────────────────────────────────

export interface Department {
  id: number
  name: string
  code: string
  color: string
  description: string
  address: string
  phone: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface DepartmentMini {
  id: number
  name: string
  code: string
  color?: string
}

export interface DepartmentCreate {
  name: string
  code: string
  color?: string
  description?: string
  address?: string
  phone?: string
  is_active?: boolean
}

export type DepartmentUpdate = Partial<DepartmentCreate>

// ── Group (minimal) ───────────────────────────────────────────────────────────

export interface GroupMini {
  id: number
  name: string
}

// ── User-Department Role ──────────────────────────────────────────────────────

export interface UserDepartmentRole {
  id: number
  user: number
  username: string
  department: DepartmentMini
  groups: GroupMini[]
}

export interface UserDepartmentRoleMini {
  department_id: number
  department_name: string
  department_code: string
  department_color?: string
  groups: GroupMini[]
  permissions: string[]
}

export interface UserDepartmentRoleCreate {
  user: number
  department: number
  group_ids?: number[]
}

export interface UserDepartmentRoleUpdate {
  group_ids: number[]
}

// ── Active Department State ───────────────────────────────────────────────────

/** Sentinel value used in the department store to represent "All Departments" mode */
export const ALL_DEPARTMENTS_ID = null
