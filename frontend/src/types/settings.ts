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

export interface AllSettings {
  general?: GeneralSettings
  email?: EmailSettings
  member?: MemberSettings
  service?: ServiceSettings
  order?: OrderSettings
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
  }
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export type SettingsCategory = 'general' | 'email' | 'member' | 'service' | 'order'

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
  permissions: SettingsPermissions | null
  loading: boolean
  error: string | null
}
