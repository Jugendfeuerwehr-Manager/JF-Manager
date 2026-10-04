export interface PendingLegacyEntry {
  id: number
  member_id: number
  member_name: string
  department_ids: number[]
  checked: boolean
  checked_at: string | null
  notes: string
  added_at: string
}

export interface PendingLegacyAttachment {
  id: number
  name: string
  description: string
  file_size: number
  mime_type: string
}

export interface LegacyListTarget {
  department: number
  list_id: number
}

export interface PendingLegacyList {
  id: number
  name: string
  description: string
  entries: PendingLegacyEntry[]
  attachments: PendingLegacyAttachment[]
  targets: LegacyListTarget[]
}

export interface ResolveLegacyListInput {
  department: number
  entry_ids: number[]
  attachment_ids: number[]
  target_list_id?: number
  assign_description: boolean
  complete: boolean
}

export interface ResolveLegacyListResult {
  target_list_id: number
  complete: boolean
  pending: PendingLegacyList | null
}
