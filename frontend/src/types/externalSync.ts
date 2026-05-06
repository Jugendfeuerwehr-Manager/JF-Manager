import type { PaginatedResponse } from '@/types/common'

export type SyncProvider = 'spond' | 'hi_org'
export type SyncScope = 'organization' | 'department'
export type SyncRunMode = 'manual' | 'interval'
export type SyncDeletionMode = 'review' | 'auto_delete'
export type SyncRunStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'cancelled'

export interface SyncJob {
  id: number
  name: string
  provider: SyncProvider
  scope: SyncScope
  department: number | null
  department_name: string | null
  run_mode: SyncRunMode
  interval_minutes: number | null
  deletion_mode: SyncDeletionMode
  enabled: boolean
  has_credentials: boolean
  last_run_at: string | null
  next_run_at: string | null
  last_success_at: string | null
  last_error: string
  last_tested_at: string | null
  last_test_status: boolean | null
  created_at: string
  updated_at: string
  config?: Record<string, unknown>
  recent_runs?: SyncRun[]
}

export interface SyncJobCreate {
  name: string
  provider: SyncProvider
  scope: SyncScope
  department: number | null
  run_mode: SyncRunMode
  interval_minutes: number | null
  deletion_mode: SyncDeletionMode
  enabled: boolean
  config?: Record<string, unknown>
  credentials?: Record<string, unknown>
}

export interface SyncRun {
  id: number
  job: number
  job_name: string
  provider: SyncProvider
  department: number | null
  status: SyncRunStatus
  trigger: string
  summary: Record<string, unknown>
  imported_members: number
  imported_groups: number
  updated_members: number
  updated_groups: number
  flagged_for_review: number
  deleted_objects: number
  started_at: string | null
  finished_at: string | null
  error_message: string
  created_at: string
}

export interface SyncBindingPreview {
  id: number
  job: number
  job_name: string
  object_type: 'member' | 'group'
  external_id: string
  external_name: string
  is_deleted_in_source: boolean
  pending_garbage_collection: boolean
  override_local_changes: boolean
  managed_fields: string[]
  last_seen_at: string | null
  created_at: string
  updated_at: string
}

export interface GarbageCollectionPreview {
  job: number
  pending_count: number
  items: SyncBindingPreview[]
}

export interface GarbageCollectionResult {
  job: number
  deleted_count: number
}

export type SyncJobListResponse = PaginatedResponse<SyncJob>
export type SyncRunListResponse = PaginatedResponse<SyncRun>
