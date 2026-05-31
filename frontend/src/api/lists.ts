import apiClient from './index'
import type { MemberList, MemberListCreate, MemberListDetail, MemberListUpdate, CreateFromEventTypeParams } from '@/types/lists'
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

  bulkAdd(listId: number, memberIds: number[]) {
    return apiClient.post<{ added: number; member_count: number }>(
      `/member-lists/${listId}/bulk_add/`,
      { member_ids: memberIds },
    )
  },

  toggleCheck(listId: number, memberId: number) {
    return apiClient.post<{ checked: boolean; checked_at: string | null }>(
      `/member-lists/${listId}/toggle_check/`,
      { member_id: memberId },
    )
  },

  setCheck(listId: number, memberId: number, checked: boolean) {
    return apiClient.post<{ checked: boolean; checked_at: string | null }>(
      `/member-lists/${listId}/set_check/`,
      { member_id: memberId, checked },
    )
  },

  checkAll(listId: number) {
    return apiClient.post<{ checked_count: number }>(`/member-lists/${listId}/check_all/`)
  },

  uncheckAll(listId: number) {
    return apiClient.post<{ checked_count: number }>(`/member-lists/${listId}/uncheck_all/`)
  },

  updateEntryNotes(listId: number, memberId: number, notes: string) {
    return apiClient.patch<{ notes: string }>(
      `/member-lists/${listId}/update_entry_notes/`,
      { member_id: memberId, notes },
    )
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
