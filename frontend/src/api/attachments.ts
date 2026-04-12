import apiClient from './index'
import type { Attachment, AttachmentCreate, PaginatedResponse } from '@/types/api'

export type { Attachment, AttachmentCreate }

export interface AttachmentListParams {
  content_type?: number
  object_id?: number
  limit?: number
  offset?: number
}

export const attachmentsApi = {
  list(params?: AttachmentListParams) {
    return apiClient.get<PaginatedResponse<Attachment>>('/attachments/', { params })
  },

  get(id: number) {
    return apiClient.get<Attachment>(`/attachments/${id}/`)
  },

  create(data: FormData) {
    return apiClient.post<Attachment>('/attachments/', data, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  update(id: number, data: FormData | Partial<AttachmentCreate>) {
    const headers = data instanceof FormData ? { 'Content-Type': 'multipart/form-data' } : {}
    return apiClient.patch<Attachment>(`/attachments/${id}/`, data, { headers })
  },

  delete(id: number) {
    return apiClient.delete(`/attachments/${id}/`)
  },

  // Get attachments for a specific member
  getForMember(memberId: number) {
    return apiClient.get<Attachment[]>(`/members/${memberId}/attachments/`)
  },

  download(id: number) {
    return apiClient.get(`/attachments/${id}/download/`, {
      responseType: 'blob'
    })
  }
}
