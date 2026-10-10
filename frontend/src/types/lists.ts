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
  /** Rises with every change; sent back as `expected_version` to detect conflicts (UX-03.2). */
  version: number
}

/** Server state of one entry, returned after a write and inside a 409 conflict. */
export interface MemberListEntryState {
  id: number
  member_id: number
  checked: boolean
  checked_at: string | null
  notes: string
  version: number
}

export interface MemberListEntryConflict {
  detail: string
  code: 'conflict'
  current: MemberListEntryState
}

/** Preview of a bulk check/uncheck: exactly these entries would change. */
export interface BulkCheckPreview {
  dry_run: true
  count: number
  entries: Array<{ member_id: number; name: string; version: number }>
}

export interface BulkCheckResult {
  dry_run: false
  changed: number
  skipped: number
  checked_count: number
  entries: MemberListEntryState[]
}

export interface BulkAddResult {
  dry_run: boolean
  added: number
  already_in_list: number
  members: Array<{ member_id: number; name: string }>
  member_count: number
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
