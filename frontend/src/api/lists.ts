import apiClient from './index'
import type {
  BulkAddResult,
  BulkCheckPreview,
  BulkCheckResult,
  CreateFromEventTypeParams,
  MemberList,
  MemberListCreate,
  MemberListDetail,
  MemberListEntryState,
  MemberListUpdate,
} from '@/types/lists'
import type { PaginatedResponse } from '@/types/api'
import type { Attachment } from '@/types/qualifications'

export const memberListsApi = {
  list() {
    return apiClient.get<PaginatedResponse<MemberList>>('/member-lists/')
  },

  get(id: number) {
    return apiClient.get<MemberListDetail>(`/member-lists/${id}/`)
  },

  create(data: MemberListCreate) {
    return apiClient.post<MemberList>('/member-lists/', data)
  },

  update(id: number, data: MemberListUpdate) {
    return apiClient.patch<MemberList>(`/member-lists/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/member-lists/${id}/`)
  },

  addMember(listId: number, memberId: number) {
    return apiClient.post<{ added: boolean; member_count: number }>(
      `/member-lists/${listId}/add_member/`,
      { member_id: memberId },
    )
  },

  removeMember(listId: number, memberId: number) {
    return apiClient.post<{ removed: boolean; member_count: number }>(
      `/member-lists/${listId}/remove_member/`,
      { member_id: memberId },
    )
  },

  /** With `dryRun` nothing is written; the answer names who would be added. */
  bulkAdd(listId: number, memberIds: number[], dryRun = false) {
    return apiClient.post<BulkAddResult>(`/member-lists/${listId}/bulk_add/`, { member_ids: memberIds, dry_run: dryRun })
  },

  /** Sets one entry; `expectedVersion` makes a stale write fail with 409 and the current state. */
  setCheck(listId: number, memberId: number, checked: boolean, expectedVersion?: number) {
    return apiClient.post<MemberListEntryState>(`/member-lists/${listId}/set_check/`, {
      member_id: memberId,
      checked,
      ...(expectedVersion ? { expected_version: expectedVersion } : {}),
    })
  },

  previewBulkCheck(listId: number, checked: boolean) {
    return apiClient.post<BulkCheckPreview>(`/member-lists/${listId}/${checked ? 'check_all' : 'uncheck_all'}/`, { dry_run: true })
  },

  /** Applies a previewed bulk change to exactly the previewed members. */
  applyBulkCheck(listId: number, checked: boolean, memberIds: number[]) {
    return apiClient.post<BulkCheckResult>(`/member-lists/${listId}/${checked ? 'check_all' : 'uncheck_all'}/`, { member_ids: memberIds })
  },

  updateEntryNotes(listId: number, memberId: number, notes: string, expectedVersion?: number) {
    return apiClient.patch<MemberListEntryState>(`/member-lists/${listId}/update_entry_notes/`, {
      member_id: memberId,
      notes,
      ...(expectedVersion ? { expected_version: expectedVersion } : {}),
    })
  },

  attachments: {
    list(listId: number) {
      return apiClient.get<Attachment[]>(`/member-lists/${listId}/attachments/`)
    },
    upload(listId: number, data: FormData) {
      return apiClient.post<Attachment>(`/member-lists/${listId}/attachments/`, data, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    delete(listId: number, attachmentId: number) {
      return apiClient.delete(`/member-lists/${listId}/attachments/${attachmentId}/`)
    },
  },

  exportExcel(listId: number, columns?: string[]) {
    const params: Record<string, string> = {}
    if (columns && columns.length > 0) {
      params.columns = columns.join(',')
    }
    return apiClient.get(`/member-lists/${listId}/export-excel/`, {
      params,
      responseType: 'blob',
    })
  },

  createFromEventType(params: CreateFromEventTypeParams, department?: number | null) {
    const queryParams = department != null ? { department } : undefined
    return apiClient.post<MemberList>('/member-lists/create_from_event_type/', params, { params: queryParams })
  },
}
