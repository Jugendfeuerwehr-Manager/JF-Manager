/**
 * TypeScript types for Member Events and Event Types.
 * Canonical source — import from here, not from @/types/api.
 */

export interface EventType {
  id: number
  name: string
  department: number | null
  event_count?: number
}

export interface EventTypeCreate {
  name: string
  department?: number | null
}

export interface Event {
  id: number
  member: number
  member_name: string
  type: number | null
  event_type: EventType | null
  datetime: string
  notes: string
  /** Who created the entry; null for entries created before this was recorded. */
  created_by_name: string | null
  created_at: string | null
}

export interface EventCreate {
  member: number
  type: number
  datetime: string
  notes?: string
}
