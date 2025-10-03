// Auto-generated TypeScript types from OpenAPI schema

export interface Member {
  id: number
  name: string
  lastname: string
  full_name: string
  birthday: string | null
  age: number
  email: string
  street: string
  zip_code: string
  city: string
  phone: string
  mobile: string
  notes: string
  joined: string | null
  identityCardNumber: string
  canSwimm: boolean
  status: Status | null
  group: Group | null
  storage_location: number | null
  avatar: string | null
  avatar_url: string | null
  parents?: Parent[]
}

export interface MemberCreate {
  name: string
  lastname: string
  birthday?: string | null
  email?: string
  street?: string
  zip_code?: string
  city?: string
  phone?: string
  mobile?: string
  notes?: string
  joined?: string | null
  identityCardNumber?: string
  canSwimm?: boolean
  status?: number | null
  group?: number | null
  storage_location?: number | null
  avatar?: File | null
}

export interface Status {
  id: number
  name: string
  color: string
}

export interface Group {
  id: number
  name: string
}

export interface Parent {
  id: number
  name: string
  lastname: string
  full_name: string
  email: string
  email2: string
  phone: string
  mobile: string
  street: string
  zip_code: string
  city: string
  notes: string
  children: number[]
}

export interface Event {
  id: number
  member: number
  member_name: string
  type: number | null
  event_type: EventType | null
  datetime: string
  notes: string
}

export interface EventType {
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
  groups: UserGroup[]
  permissions: string[]
}

export interface UserGroup {
  id: number
  name: string
}

export interface AppSettings {
  app_name: string
  organization_name: string
  contact_email: string
  equipment_manager_email: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

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

// Inventory types
export interface Category {
  id: number
  name: string
  description: string
}

export interface Item {
  id: number
  name: string
  category: number
  description: string
}

export interface StorageLocation {
  id: number
  name: string
  full_path: string
}

// Orders types
export interface Order {
  id: number
  member: number
  created_at: string
  status: string
}

export interface OrderableItem {
  id: number
  name: string
  description: string
  sizes_list: string[]
}

// Servicebook types
export interface Service {
  id: number
  date: string
  title: string
  description: string
}

export interface Attendance {
  id: number
  service: number
  member: number
  attended: boolean
}

// Qualifications types
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
  user: number | null
  member: number | null
  date_acquired: string
  date_expires: string | null
  issued_by: string
}
