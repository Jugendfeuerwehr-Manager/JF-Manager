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
}

export type MemberListUpdate = Partial<MemberListCreate>
