import type { PaginatedResponse } from '@/types/api'

export interface Permission {
  id: number
  name: string
  codename: string
  app_label: string
  model: string
  full_codename: string
  description: string
}

export interface AuthGroup {
  id: number
  name: string
  user_count: number
  permissions_count: number
}

export interface AuthGroupDetail {
  id: number
  name: string
  permissions: Permission[]
  users: number[]
}

export interface AuthGroupWrite {
  name: string
  permission_ids: number[]
}

export interface AdminUser {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  mobile_phone: string
  street: string
  zip_code: string
  city: string
  is_staff: boolean
  is_active: boolean
  is_superuser: boolean
  dsgvo_internal: boolean
  dsgvo_external: boolean
  email_signature: string
  theme_mode: string
  date_joined: string
  last_login: string | null
  groups: AuthGroup[]
}

export interface AdminUserDetail extends AdminUser {
  permissions: string[]
}

export interface AdminUserWrite {
  username: string
  email: string
  first_name: string
  last_name: string
  phone?: string
  mobile_phone?: string
  street?: string
  zip_code?: string
  city?: string
  is_staff: boolean
  is_active: boolean
  is_superuser: boolean
  dsgvo_internal?: boolean
  dsgvo_external?: boolean
  email_signature?: string
  theme_mode?: string
  password?: string
  group_ids: number[]
}

export type PaginatedAdminUsers = PaginatedResponse<AdminUser>
export type PaginatedAuthGroups = PaginatedResponse<AuthGroup>
export type PaginatedPermissions = PaginatedResponse<Permission>

// Permission categories for the UI
export interface PermissionCategory {
  label: string
  icon: string
  permissions: Permission[]
}
