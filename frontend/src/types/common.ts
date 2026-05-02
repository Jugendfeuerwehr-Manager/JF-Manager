/**
 * Shared/common TypeScript types used across multiple domains.
 *
 * Includes: auth types, pagination wrapper, user profile, app settings.
 */
import type { UserDepartmentRoleMini } from './departments'

// ── Pagination ──────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access: string
  refresh: string
}

export interface TokenRefreshRequest {
  refresh: string
}

export interface TokenRefreshResponse {
  access: string
  refresh?: string
}

// ── User profile ─────────────────────────────────────────────────────────────

export interface UserGroup {
  id: number
  name: string
}

export interface UserInfo {
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
  date_joined: string
  last_login: string | null
  avatar: string | null
  avatar_url: string | null
  dsgvo_internal: boolean
  dsgvo_external: boolean
  email_signature?: string
  theme_mode?: 'light' | 'dark' | 'system'
  groups: UserGroup[]
  permissions: string[]
  department_roles: UserDepartmentRoleMini[]
  has_org_wide_access: boolean
  favorite_department: number | null
}

// ── App settings ─────────────────────────────────────────────────────────────

export interface AppSettings {
  app_name: string
  organization_name: string
  contact_email: string
  equipment_manager_email: string
  service_start_time: string  // "HH:mm"
  service_end_time: string    // "HH:mm"
}
