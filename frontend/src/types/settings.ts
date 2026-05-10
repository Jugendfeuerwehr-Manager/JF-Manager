/**
 * Settings Types
 * TypeScript interfaces for application settings management
 */

// ============================================================================
// Settings Interfaces
// ============================================================================

export interface GeneralSettings {
  title: string
}

export interface EmailSettings {
  email_host: string
  email_port: number
  email_use_tls: boolean
  email_use_ssl: boolean
  email_host_user: string
  email_host_password?: string  // Write-only field
  default_from_email: string
}

export interface MemberSettings {
  alert_threshold: number
  alert_threshold_last_entries: number
}

export interface ServiceSettings {
  service_start_time: string  // Format: "HH:MM"
  service_end_time: string    // Format: "HH:MM"
}

export interface OrderSettings {
  equipment_manager_email: string
}

export interface LdapSettings {
  enabled: boolean
  server_uri: string
  start_tls: boolean
  bind_dn: string
  bind_password?: string
  has_bind_password: boolean
  user_search_base_dn: string
  user_search_filter: string
  group_search_base_dn: string
  group_search_filter: string
  group_type: 'group_of_names' | 'active_directory'
  mirror_groups: boolean
  require_group: string
}

export interface AllSettings {
  general?: GeneralSettings
  email?: EmailSettings
  member?: MemberSettings
  service?: ServiceSettings
  order?: OrderSettings
  ldap?: LdapSettings
  oidc?: OidcSettingsSummary
}

/** Subset of OIDCSettings used in AllSettings (mirrors backend OIDCSettingsSerializer) */
export interface OidcSettingsSummary {
  enabled: boolean
  provider_name: string
  issuer_url: string
  client_id: string
  has_client_secret: boolean
  scope: string
  groups_claim: string
  staff_group: string
  admin_group: string
  require_group_mapping: boolean
  hide_local_login: boolean
}

// ============================================================================
// LDAP Department Role Mapping Types
// ============================================================================

export interface AuthGroupMini {
  id: number
  name: string
}

export interface LdapDepartmentRoleMapping {
  id: number
  ldap_group_dn: string
  department: number
  department_name: string
  auth_groups: AuthGroupMini[]
  auth_group_ids: number[]
  revoke_on_mismatch: boolean
}

export interface LdapDepartmentRoleMappingCreate {
  ldap_group_dn: string
  department: number
  auth_group_ids?: number[]
  revoke_on_mismatch?: boolean
}

export interface LdapBrowseRequest {
  base_dn: string
  filter?: string
  scope?: 'one' | 'subtree'
  attributes?: string[]
}

export interface LdapBrowseEntry {
  dn: string
  cn?: string | string[]
  ou?: string | string[]
  description?: string | string[]
  objectClass?: string | string[]
  [key: string]: string | string[] | undefined
}

export interface LdapBrowseResult {
  ok: boolean
  entries: LdapBrowseEntry[]
  total: number
  detail?: string
}

// ============================================================================
// Permissions Interfaces
// ============================================================================

export interface CategoryPermissions {
  can_view: boolean
  can_change: boolean
}

export interface SettingsPermissions {
  can_view_all: boolean
  can_change_all: boolean
  categories: {
    general: CategoryPermissions
    email: CategoryPermissions
    member: CategoryPermissions
    service: CategoryPermissions
    order: CategoryPermissions
    ldap: CategoryPermissions
    oidc: CategoryPermissions
    [key: string]: CategoryPermissions
  }
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export type SettingsCategory = 'general' | 'email' | 'email-templates' | 'member' | 'service' | 'order' | 'ldap' | 'oidc'

export interface CategorySettingsUpdate {
  category: SettingsCategory
  settings: Record<string, unknown>
}

// ============================================================================
// Tab Configuration
// ============================================================================

export interface SettingsTab {
  id: SettingsCategory
  title: string
  icon: string
  description: string
}

// ============================================================================
// Store State
// ============================================================================

export interface SettingsState {
  general: GeneralSettings | null
  email: EmailSettings | null
  member: MemberSettings | null
  service: ServiceSettings | null
  order: OrderSettings | null
  ldap: LdapSettings | null
  permissions: SettingsPermissions | null
  loading: boolean
  error: string | null
}
