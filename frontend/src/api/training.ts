import apiClient from './index'
import type {
  GenerateSeriesResult,
  LibraryBlockCategory,
  LibraryBlockCreate,
  LibraryBlockDetail,
  LibraryBlockExportPackage,
  LibraryBlockList,
  LibraryBlockTag,
  LibraryBlockUpdate,
  LibraryBlockUsageSession,
  LibraryImportResult,
  PaginatedResponse,
  TrainingBlock,
  TrainingBlockCreate,
  TrainingBlockMove,
  TrainingMedia,
  TrainingSessionCreate,
  TrainingSessionDetail,
  TrainingSessionHandout,
  TrainingSessionList,
  TrainingSessionUpdate,
} from '@/types/training'

// ─── Session API ──────────────────────────────────────────────────────────────

export const trainingSessionsApi = {
  list(params?: Record<string, unknown>) {
    return apiClient.get<PaginatedResponse<TrainingSessionList>>('/training/sessions/', { params })
  },
  get(id: number) {
    return apiClient.get<TrainingSessionDetail>(`/training/sessions/${id}/`)
  },
  create(data: TrainingSessionCreate) {
    return apiClient.post<TrainingSessionDetail>('/training/sessions/', data)
  },
  update(id: number, data: TrainingSessionUpdate) {
    return apiClient.patch<TrainingSessionDetail>(`/training/sessions/${id}/`, data)
  },
  delete(id: number) {
    return apiClient.delete(`/training/sessions/${id}/`)
  },
  handout(id: number) {
    return apiClient.get<TrainingSessionHandout>(`/training/sessions/${id}/handout/`)
  },
  generateSeries(id: number) {
    return apiClient.post<GenerateSeriesResult>(`/training/sessions/${id}/generate_series/`)
  },
}

// ─── Training Block API ───────────────────────────────────────────────────────

export const trainingBlocksApi = {
  list(params?: Record<string, unknown>) {
    return apiClient.get<PaginatedResponse<TrainingBlock>>('/training/blocks/', { params })
  },
  get(id: number) {
    return apiClient.get<TrainingBlock>(`/training/blocks/${id}/`)
  },
  create(data: TrainingBlockCreate) {
    return apiClient.post<TrainingBlock>('/training/blocks/', data)
  },
  update(id: number, data: Partial<TrainingBlockCreate>) {
    return apiClient.patch<TrainingBlock>(`/training/blocks/${id}/`, data)
  },
  delete(id: number) {
    return apiClient.delete(`/training/blocks/${id}/`)
  },
  move(id: number, data: TrainingBlockMove) {
    return apiClient.patch<TrainingBlock>(`/training/blocks/${id}/move/`, data)
  },
  uploadImage(id: number, file: File) {
    const form = new FormData()
    form.append('image', file)
    return apiClient.post<TrainingMedia>(`/training/blocks/${id}/upload_image/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  listMedia(id: number) {
    return apiClient.get<TrainingMedia[]>(`/training/blocks/${id}/media/`)
  },
  deleteMedia(id: number, mediaId: number) {
    return apiClient.delete(`/training/blocks/${id}/media/`, { params: { media_id: mediaId } })
  },
  getAttachments(id: number) {
    return apiClient.get(`/training/blocks/${id}/attachments/`)
  },
  addAttachment(id: number, data: FormData) {
    return apiClient.post(`/training/blocks/${id}/attachments/`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteAttachment(id: number, attachmentId: number) {
    return apiClient.delete(`/training/blocks/${id}/attachments/`, {
      data: { attachment_id: attachmentId },
    })
  },
}

// ─── Library API ──────────────────────────────────────────────────────────────

export const libraryApi = {
  list(params?: Record<string, unknown>) {
    return apiClient.get<PaginatedResponse<LibraryBlockList>>('/training/library/', { params })
  },
  get(id: number) {
    return apiClient.get<LibraryBlockDetail>(`/training/library/${id}/`)
  },
  create(data: LibraryBlockCreate) {
    return apiClient.post<LibraryBlockDetail>('/training/library/', data)
  },
  update(id: number, data: LibraryBlockUpdate) {
    return apiClient.patch<LibraryBlockDetail>(`/training/library/${id}/`, data)
  },
  delete(id: number) {
    return apiClient.delete(`/training/library/${id}/`)
  },
  uploadImage(id: number, file: File) {
    const form = new FormData()
    form.append('image', file)
    return apiClient.post<TrainingMedia>(`/training/library/${id}/upload_image/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  listMedia(id: number) {
    return apiClient.get<TrainingMedia[]>(`/training/library/${id}/media/`)
  },
  deleteMedia(id: number, mediaId: number) {
    return apiClient.delete(`/training/library/${id}/media/`, { params: { media_id: mediaId } })
  },
  exportBlocks(ids: number[]) {
    return apiClient.post<LibraryBlockExportPackage>('/training/library/export_blocks/', { ids })
  },
  importBlocks(pkg: LibraryBlockExportPackage) {
    return apiClient.post<LibraryImportResult>('/training/library/import_blocks/', pkg)
  },
  usages(id: number) {
    return apiClient.get<LibraryBlockUsageSession[]>(`/training/library/${id}/usages/`)
  },
  getAttachments(id: number) {
    return apiClient.get(`/training/library/${id}/attachments/`)
  },
  addAttachment(id: number, data: FormData) {
    return apiClient.post(`/training/library/${id}/attachments/`, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteAttachment(id: number, attachmentId: number) {
    return apiClient.delete(`/training/library/${id}/attachments/`, {
      data: { attachment_id: attachmentId },
    })
  },
}

// ─── Library Categories & Tags API ───────────────────────────────────────────

export const libraryCategoriesApi = {
  list() {
    return apiClient.get<PaginatedResponse<LibraryBlockCategory>>('/training/library/categories/')
  },
  create(data: Omit<LibraryBlockCategory, 'id'>) {
    return apiClient.post<LibraryBlockCategory>('/training/library/categories/', data)
  },
  update(id: number, data: Partial<LibraryBlockCategory>) {
    return apiClient.patch<LibraryBlockCategory>(`/training/library/categories/${id}/`, data)
  },
  delete(id: number) {
    return apiClient.delete(`/training/library/categories/${id}/`)
  },
}

export const libraryTagsApi = {
  list() {
    return apiClient.get<PaginatedResponse<LibraryBlockTag>>('/training/library/tags/')
  },
  create(data: { name: string }) {
    return apiClient.post<LibraryBlockTag>('/training/library/tags/', data)
  },
  delete(id: number) {
    return apiClient.delete(`/training/library/tags/${id}/`)
  },
}
