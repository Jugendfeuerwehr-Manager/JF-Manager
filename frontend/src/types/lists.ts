/**
 * TypeScript types for the MemberLists domain.
 */

import type { Member } from '@/types/members'

export interface MemberListEntry {
  id: number
  member: Member
  checked: boolean
  checked_at: string | null
  notes: string
  added_at: string
}

export interface MemberList {
  id: number
  name: string
  description: string
  color: string
  department: number | null
  /** Lists of an organization without departments; `department` is null. */
  organization_wide: boolean
  member_count: number
  checked_count: number
  created_at: string
  updated_at: string
}

export interface MemberListDetail extends MemberList {
  entries: MemberListEntry[]
}

export interface MemberListCreate {
  name: string
  description?: string
  color?: string
  /** `null` creates an organization-wide list (only while no active department exists). */
  department: number | null
}

export type MemberListUpdate = Partial<MemberListCreate>

export interface CreateFromEventTypeParams {
  name: string
  department?: number | null
  description?: string
  event_type_id?: number | null
  invert: boolean
  date_from?: string | null
  date_to?: string | null
}
