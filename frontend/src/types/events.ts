/**
 * TypeScript types for Member Events and Event Types.
 * Canonical source — import from here, not from @/types/api.
 */

export interface EventType {
  id: number
  name: string
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

export interface EventCreate {
  member: number
  type: number
  datetime: string
  notes?: string
}
