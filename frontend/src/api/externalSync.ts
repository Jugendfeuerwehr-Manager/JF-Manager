import apiClient from './index'
import type {
  GarbageCollectionPreview,
  GarbageCollectionResult,
  SpondGroupsLookupRequest,
  SpondTopLevelGroupResponse,
  SyncJob,
  SyncJobCreate,
  SyncJobListResponse,
  SyncRun,
  SyncRunListResponse,
} from '@/types/externalSync'

export const externalSyncApi = {
  listJobs(params?: Record<string, unknown>) {
    return apiClient.get<SyncJobListResponse>('/sync-jobs/', { params })
  },

  createJob(data: SyncJobCreate) {
    return apiClient.post<SyncJob>('/sync-jobs/', data)
  },

  deleteJob(id: number) {
    return apiClient.delete(`/sync-jobs/${id}/`)
  },

  testConnection(id: number) {
    return apiClient.post(`/sync-jobs/${id}/test_connection/`, {})
  },

  listSpondTopLevelGroups(data: SpondGroupsLookupRequest) {
    return apiClient.post<SpondTopLevelGroupResponse>('/sync-jobs/spond-top-level-groups/', data)
  },

  runNow(id: number) {
    return apiClient.post<SyncRun>(`/sync-jobs/${id}/run_now/`, {})
  },

  getGarbageCollectionPreview(id: number) {
    return apiClient.get<GarbageCollectionPreview>(`/sync-jobs/${id}/garbage-collection-preview/`)
  },

  garbageCollect(id: number) {
    return apiClient.post<GarbageCollectionResult>(`/sync-jobs/${id}/garbage-collect/`, {})
  },

  listRuns(params?: Record<string, unknown>) {
    return apiClient.get<SyncRunListResponse>('/sync-runs/', { params })
  },
}
