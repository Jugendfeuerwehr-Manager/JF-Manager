import apiClient from './index'
import type {
  BlockAttachment,
  GenerateSeriesResult,
  InstructorMini,
  LibraryBlockCategory,
  LibraryBlockCreate,
  LibraryBlockDetail,
  LibraryBlockExportPackage,
  LibraryBlockList,
  LibraryBlockTag,
  LibraryBlockUpdate,
  LibraryBlockUsageSession,
  LibraryImportResult,
  MaterialOption,
  PaginatedResponse,
  PlanWarning,
  PropagationPreview,
  SeriesPreview,
  SeriesWindow,
  TrainingBlock,
  TrainingBlockCreate,
  TrainingBlockMove,
  TrainingMedia,
  TrainingPlanDraft,
  TrainingSessionCreate,
  TrainingSessionDetail,
  TrainingSessionHandout,
  TrainingSessionList,
  TrainingSessionUpdate,
  TrainingTemplate,
  TrainingTemplateDetail,
  TrainingDebrief,
  TrainingDebriefInput,
} from '@/types/training'

// ─── Session API ──────────────────────────────────────────────────────────────

export const trainingSessionsApi = {
  plan(id: number) {
    return apiClient.get<TrainingSessionDetail>(`/training/sessions/${id}/plan/`)
  },
  savePlan(id: number, data: TrainingPlanDraft) {
    return apiClient.put<TrainingSessionDetail>(`/training/sessions/${id}/plan/`, data)
  },
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
  delete(id: number, params?: { delete_linked_service?: boolean }) {
    return apiClient.delete(`/training/sessions/${id}/`, { params })
  },
  handout(id: number) {
    return apiClient.get<TrainingSessionHandout>(`/training/sessions/${id}/handout/`)
  },
  seriesPreview(id: number, params?: SeriesWindow) {
    return apiClient.get<SeriesPreview>(`/training/sessions/${id}/series_preview/`, { params })
  },
  generateSeries(id: number, data: SeriesWindow & { preview_token: string }) {
    return apiClient.post<GenerateSeriesResult>(`/training/sessions/${id}/generate_series/`, data)
  },
  debrief(id: number) {
    return apiClient.get<TrainingDebrief>(`/training/sessions/${id}/debrief/`)
  },
  saveDebrief(id: number, data: TrainingDebriefInput) {
    return apiClient.put<TrainingDebrief>(`/training/sessions/${id}/debrief/`, data)
  },
  checkPlan(id: number, data: TrainingPlanDraft) {
    return apiClient.post<{ warnings: PlanWarning[] }>(`/training/sessions/${id}/check_plan/`, data)
  },
  instructorOptions(id: number) {
    return apiClient.get<InstructorMini[]>(`/training/sessions/${id}/instructor_options/`)
  },
  materialOptions(id: number, search = '') {
    return apiClient.get<MaterialOption[]>(`/training/sessions/${id}/material_options/`, { params: search ? { search } : {} })
  },
  saveAsTemplate(id: number, data: { title?: string }) {
    return apiClient.post<TrainingTemplate>(`/training/sessions/${id}/save_as_template/`, data)
  },
  copy(id: number, data: { date: string; title?: string }) {
    return apiClient.post<TrainingSessionDetail>(`/training/sessions/${id}/copy/`, data)
  },
  propagationPreview(id: number, data: { include_deviating?: number[] }) {
    return apiClient.post<PropagationPreview>(`/training/sessions/${id}/propagation_preview/`, data)
  },
  propagateSeries(id: number, data: { include_deviating?: number[]; preview_token: string }) {
    return apiClient.post<{ updated: number; session_ids: number[] }>(`/training/sessions/${id}/propagate_series/`, data)
  },
}

// ─── Exercise templates ─────────────────────────────────────────────────────

export const trainingTemplatesApi = {
  list(params?: Record<string, unknown>) {
    return apiClient.get<PaginatedResponse<TrainingTemplate>>('/training/templates/', { params })
  },
  get(id: number) {
    return apiClient.get<TrainingTemplateDetail>(`/training/templates/${id}/`)
  },
  update(id: number, data: { title?: string; description?: string }) {
    return apiClient.patch<TrainingTemplate>(`/training/templates/${id}/`, data)
  },
  delete(id: number) {
    return apiClient.delete(`/training/templates/${id}/`)
  },
  instantiate(id: number, data: { date: string; title?: string }) {
    return apiClient.post<TrainingSessionDetail>(`/training/templates/${id}/instantiate/`, data)
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
    return apiClient.get<BlockAttachment[]>(`/training/blocks/${id}/attachments/`)
  },
  addAttachment(id: number, data: FormData) {
    return apiClient.post<BlockAttachment>(`/training/blocks/${id}/attachments/`, data, {
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
    return apiClient.get<BlockAttachment[]>(`/training/library/${id}/attachments/`)
  },
  addAttachment(id: number, data: FormData) {
    return apiClient.post<BlockAttachment>(`/training/library/${id}/attachments/`, data, {
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
