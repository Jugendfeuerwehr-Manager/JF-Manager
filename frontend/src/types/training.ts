// ─── Shared ──────────────────────────────────────────────────────────────────

export interface GroupMini {
  id: number
  name: string
}

export interface TrainingMedia {
  id: number
  url: string
  original_filename: string
  created_at: string
}

// ─── Library Block Category & Tag ────────────────────────────────────────────

export interface LibraryBlockCategory {
  id: number
  name: string
  color: string
  icon: string
}

export interface LibraryBlockTag {
  id: number
  name: string
}

// ─── Library Block ────────────────────────────────────────────────────────────

export interface LibraryBlockList {
  id: number
  export_uuid: string
  title: string
  description: string
  default_duration_minutes: number
  category: number | null
  category_name: string | null
  category_color: string | null
  tags: LibraryBlockTag[]
  color: string
  is_public: boolean
  created_at: string
  usage_count: number
  last_used_date: string | null
}

export interface LibraryBlockDetail {
  id: number
  export_uuid: string
  title: string
  description: string
  content: string
  default_duration_minutes: number
  category: LibraryBlockCategory | null
  category_id?: number | null
  tags: LibraryBlockTag[]
  tag_ids?: number[]
  color: string
  nextcloud_folder_url: string
  is_public: boolean
  source_instance_url: string
  created_by: number | null
  created_at: string
  updated_at: string
  media: TrainingMedia[]
}

export interface LibraryBlockCreate {
  title: string
  description?: string
  content?: string
  default_duration_minutes?: number
  category_id?: number | null
  tag_ids?: number[]
  color?: string
  nextcloud_folder_url?: string
  is_public?: boolean
}

export type LibraryBlockUpdate = Partial<LibraryBlockCreate>

// Federation export/import
export interface LibraryBlockExportPackage {
  jf_manager_version: '1.0'
  export_date: string
  source_instance: string
  blocks: LibraryBlockExportItem[]
}

export interface LibraryBlockExportItem {
  export_uuid: string
  title: string
  description: string
  content: string
  default_duration_minutes: number
  category: string | null
  tags: string[]
  color: string
  nextcloud_folder_url: string
}

export interface LibraryImportResult {
  created: number
  updated: number
  errors: Array<{ block: string; error: string }>
}

// Lightweight session info returned by the library block usages endpoint
export interface LibraryBlockUsageSession {
  id: number
  title: string
  date: string
  start_time: string
  end_time: string
  location: string
  group_count: number
  groups: GroupMini[]
  block_count: number
}

// ─── Training Block ───────────────────────────────────────────────────────────

export interface TrainingBlock {
  id: number
  title: string
  content: string
  session: number
  groups: GroupMini[]
  library_block: number | null
  library_block_title: string | null
  duration_minutes: number
  start_offset_minutes: number
  position_order: number
  color: string
  nextcloud_folder_url: string
  created_at: string
  updated_at: string
  media: TrainingMedia[]
}

export interface TrainingBlockCreate {
  title: string
  content?: string
  session: number
  group_ids?: number[]
  library_block?: number | null
  duration_minutes?: number
  start_offset_minutes?: number
  position_order?: number
  color?: string
  nextcloud_folder_url?: string
}

export interface TrainingBlockMove {
  start_offset_minutes?: number
  position_order?: number
  duration_minutes?: number
  groups?: number[]
}

// ─── Training Session ─────────────────────────────────────────────────────────

export type RecurrenceFrequency = 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY'

export interface RecurrenceRule {
  frequency: RecurrenceFrequency
  end_date: string // ISO date string
}

export interface TrainingSessionList {
  id: number
  title: string
  date: string
  start_time: string
  end_time: string
  location: string
  group_count: number
  groups: GroupMini[]
  block_count: number
  series_parent: number | null
  recurrence_rule: RecurrenceRule | null
}

export interface TrainingSessionDetail {
  id: number
  title: string
  description: string
  date: string
  start_time: string
  end_time: string
  location: string
  notes: string
  groups: GroupMini[]
  group_ids?: number[]
  blocks: TrainingBlock[]
  series_parent: number | null
  recurrence_rule: RecurrenceRule | null
  created_by: number | null
  created_by_name: string | null
  created_at: string
  updated_at: string
}

export interface TrainingSessionCreate {
  title: string
  description?: string
  date: string
  start_time: string
  end_time: string
  location?: string
  notes?: string
  group_ids?: number[]
  recurrence_rule?: RecurrenceRule | null
}

export type TrainingSessionUpdate = Partial<TrainingSessionCreate>

export interface TrainingSessionHandout {
  id: number
  title: string
  description: string
  date: string
  start_time: string
  end_time: string
  location: string
  notes: string
  groups: GroupMini[]
  blocks: TrainingBlock[]
}

// ─── Planner ui state ────────────────────────────────────────────────────────

export interface PlannerBlock extends TrainingBlock {
  // computed in planner store
  groupIds: number[]
  allGroups: boolean // true when groups is empty
}

export interface GenerateSeriesResult {
  created: number
  session_ids: number[]
}

// ─── Paginated responses ─────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
