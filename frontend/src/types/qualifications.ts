/**
 * TypeScript types for Qualifications & Special Tasks module
 * Follows pagination pattern from orders.ts
 */

// ==================== Base Models ====================

export interface QualificationType {
  id: number
  name: string
  expires: boolean
  validity_period: number | null
  description: string
}

export interface Qualification {
  id: number
  type: number
  type_name: string
  type_details?: QualificationType
  user: number | null
  user_name: string | null
  member: number | null
  member_name: string | null
  person_name: string
  date_acquired: string
  date_expires: string | null
  issued_by: string
  note: string
  // Computed fields
  is_expired: boolean
  expires_soon: boolean
  status_class: string
  attachments?: Attachment[]
}

export interface SpecialTaskType {
  id: number
  name: string
  description: string
}

export interface SpecialTask {
  id: number
  task: number
  task_name: string
  task_details?: SpecialTaskType
  user: number | null
  user_name: string | null
  member: number | null
  member_name: string | null
  person_name: string
  start_date: string
  end_date: string | null
  note: string
  // Computed fields
  is_active: boolean
  duration_days: number
  status_class: string
  attachments?: Attachment[]
}

export interface Attachment {
  id: number
  name: string
  description?: string
  file?: string  // REST API field
  file_url?: string  // Legacy view field
  file_size?: string  // Legacy view field (human readable)
  uploaded_at: string
  uploaded_by?: number
  uploaded_by_name?: string
}

// ==================== Paginated Responses ====================

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ==================== Create/Update DTOs ====================

export interface QualificationCreate {
  type: number
  user?: number | null
  member?: number | null
  date_acquired: string
  date_expires?: string | null
  issued_by?: string
  note?: string
}

export interface QualificationUpdate {
  type?: number
  user?: number | null
  member?: number | null
  date_acquired?: string
  date_expires?: string | null
  issued_by?: string
  note?: string
}

export interface SpecialTaskCreate {
  task: number
  user?: number | null
  member?: number | null
  start_date: string
  end_date?: string | null
  note?: string
}

export interface SpecialTaskUpdate {
  task?: number
  user?: number | null
  member?: number | null
  start_date?: string
  end_date?: string | null
  note?: string
}

export interface QualificationTypeCreate {
  name: string
  expires: boolean
  validity_period?: number | null
  description?: string
}

export interface QualificationTypeUpdate {
  name?: string
  expires?: boolean
  validity_period?: number | null
  description?: string
}

export interface SpecialTaskTypeCreate {
  name: string
  description?: string
}

export interface SpecialTaskTypeUpdate {
  name?: string
  description?: string
}

// ==================== Filter/List Parameters ====================

export interface QualificationListParams {
  page?: number
  page_size?: number
  search?: string
  member?: number
  user?: number
  type?: number
  status?: 'all' | 'active' | 'expired' | 'expiring'
  ordering?: string
}

export interface SpecialTaskListParams {
  page?: number
  page_size?: number
  search?: string
  member?: number
  user?: number
  task?: number
  status?: 'all' | 'active' | 'ended'
  ordering?: string
}

export interface QualificationTypeListParams {
  search?: string
  expires?: boolean
  ordering?: string
}

export interface SpecialTaskTypeListParams {
  search?: string
  ordering?: string
}

// ==================== Statistics ====================

export interface QualificationStatistics {
  total_qualifications: number
  expired_qualifications: number
  expiring_qualifications: number
  active_special_tasks: number
  completed_special_tasks: number
  recent_qualifications: Qualification[]
  expiring_qualifications_list: Qualification[]
  active_special_tasks_list: SpecialTask[]
}

// ==================== API Request/Response Types ====================

export interface CalculateExpiryRequest {
  type_id: number
  date_acquired: string
}

export interface CalculateExpiryResponse {
  date_expires: string | null
}

// ==================== UI State Types ====================

export interface QualificationFormData {
  type: number | null
  user: number | null
  member: number | null
  date_acquired: string
  date_expires: string | null
  issued_by: string
  note: string
}

export interface SpecialTaskFormData {
  task: number | null
  user: number | null
  member: number | null
  start_date: string
  end_date: string | null
  note: string
}

export interface QualificationFilters {
  search: string
  type: number | null
  status: 'all' | 'active' | 'expired' | 'expiring'
  member: number | null
  user: number | null
}

export interface SpecialTaskFilters {
  search: string
  task: number | null
  status: 'all' | 'active' | 'ended'
  member: number | null
  user: number | null
}

// ==================== Dropdown Options ====================

export interface DropdownOption {
  label: string
  value: number | string
}

// ==================== Status Badge Types ====================

export type QualificationStatus = 'valid' | 'expiring' | 'expired'
export type SpecialTaskStatus = 'active' | 'ended'
export type BadgeSeverity = 'success' | 'warning' | 'danger' | 'info' | 'secondary'
