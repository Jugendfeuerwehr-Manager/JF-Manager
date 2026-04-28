/**
 * @deprecated
 * This file is a backward-compatibility re-export shim.
 *
 * Prefer importing directly from the domain-specific type file:
 *   - @/types/members   → Member, MemberCreate, Status, Group
 *   - @/types/parents   → Parent, ParentCreate
 *   - @/types/events    → Event, EventCreate, EventType
 *   - @/types/common    → UserInfo, AppSettings, PaginatedResponse, auth types
 *   - @/types/inventory → Category, Item, StorageLocation, Stock, Transaction
 *   - @/types/orders    → Order, OrderItem, OrderStatus, …
 *   - @/types/servicebook → Service, Attendance, …
 *   - @/types/qualifications → Qualification, QualificationType, …
 */

export type { Member, MemberCreate, Status, Group } from '@/types/members'
export type { Parent, ParentCreate } from '@/types/parents'
export type { Event, EventCreate, EventType } from '@/types/events'
export type {
  UserInfo,
  UserGroup,
  AppSettings,
  PaginatedResponse,
  LoginRequest,
  LoginResponse,
  TokenRefreshRequest,
  TokenRefreshResponse,
} from '@/types/common'

// Attachment types (kept here — no dedicated file yet)
export interface Attachment {
  id: number
  file: string | null
  file_url: string | null
  name: string
  description: string
  uploaded_at: string
  uploaded_by?: number
  file_size?: number
  mime_type: string
  content_type: number
  object_id: number
}

export interface AttachmentCreate {
  file: File
  name: string
  description?: string
  content_type: number
  object_id: number
}
