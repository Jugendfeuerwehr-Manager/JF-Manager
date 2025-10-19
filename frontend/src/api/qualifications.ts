/**
 * API client for Qualifications & Special Tasks
 * Follows pattern from api/orders.ts
 */
import apiClient from './index'
import type {
  QualificationType,
  Qualification,
  QualificationCreate,
  QualificationUpdate,
  QualificationTypeCreate,
  SpecialTaskType,
  SpecialTask,
  SpecialTaskCreate,
  SpecialTaskUpdate,
  SpecialTaskTypeCreate,
  PaginatedResponse,
  QualificationListParams,
  SpecialTaskListParams,
  QualificationTypeListParams,
  SpecialTaskTypeListParams,
  QualificationStatistics,
  CalculateExpiryRequest,
  CalculateExpiryResponse,
  Attachment
} from '@/types/qualifications'

// ==================== Qualification Types API ====================

export const qualificationTypesApi = {
  list(params?: QualificationTypeListParams) {
    return apiClient.get<PaginatedResponse<QualificationType>>('/qualifications/types/', {
      params
    })
  },

  get(id: number) {
    return apiClient.get<QualificationType>(`/qualifications/types/${id}/`)
  },

  create(data: QualificationTypeCreate) {
    return apiClient.post<QualificationType>('/qualifications/types/', data)
  },

  update(id: number, data: Partial<QualificationTypeCreate>) {
    return apiClient.patch<QualificationType>(`/qualifications/types/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/qualifications/types/${id}/`)
  }
}

// ==================== Qualifications API ====================

export const qualificationsApi = {
  list(params?: QualificationListParams) {
    return apiClient.get<PaginatedResponse<Qualification>>('/qualifications/', { params })
  },

  get(id: number) {
    return apiClient.get<Qualification>(`/qualifications/${id}/`)
  },

  create(data: QualificationCreate) {
    return apiClient.post<Qualification>('/qualifications/', data)
  },

  update(id: number, data: QualificationUpdate) {
    return apiClient.patch<Qualification>(`/qualifications/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/qualifications/${id}/`)
  },

  statistics() {
    return apiClient.get<QualificationStatistics>('/qualifications/statistics/')
  },

  calculateExpiry(data: CalculateExpiryRequest) {
    return apiClient.post<CalculateExpiryResponse>('/qualifications/calculate-expiry/', data)
  },

  // Attachment endpoints using REST API custom actions
  attachments: {
    list(qualificationId: number) {
      return apiClient.get<Attachment[]>(`/qualifications/${qualificationId}/attachments/`)
    },
    upload(qualificationId: number, data: FormData) {
      return apiClient.post<Attachment>(`/qualifications/${qualificationId}/attachments/`, data, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    },
    delete(qualificationId: number, attachmentId: number) {
      return apiClient.delete(`/qualifications/${qualificationId}/attachments/${attachmentId}/`)
    }
  }
}

// ==================== Special Task Types API ====================

export const specialTaskTypesApi = {
  list(params?: SpecialTaskTypeListParams) {
    return apiClient.get<PaginatedResponse<SpecialTaskType>>('/qualifications/specialtask-types/', { params })
  },

  get(id: number) {
    return apiClient.get<SpecialTaskType>(`/qualifications/specialtask-types/${id}/`)
  },

  create(data: SpecialTaskTypeCreate) {
    return apiClient.post<SpecialTaskType>('/qualifications/specialtask-types/', data)
  },

  update(id: number, data: Partial<SpecialTaskTypeCreate>) {
    return apiClient.patch<SpecialTaskType>(`/qualifications/specialtask-types/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/qualifications/specialtask-types/${id}/`)
  }
}

// ==================== Special Tasks API ====================

export const specialTasksApi = {
  list(params?: SpecialTaskListParams) {
    return apiClient.get<PaginatedResponse<SpecialTask>>('/qualifications/specialtasks/', { params })
  },

  get(id: number) {
    return apiClient.get<SpecialTask>(`/qualifications/specialtasks/${id}/`)
  },

  create(data: SpecialTaskCreate) {
    return apiClient.post<SpecialTask>('/qualifications/specialtasks/', data)
  },

  update(id: number, data: SpecialTaskUpdate) {
    return apiClient.patch<SpecialTask>(`/qualifications/specialtasks/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/qualifications/specialtasks/${id}/`)
  },

  endTask(id: number) {
    return apiClient.post<SpecialTask>(`/qualifications/specialtasks/${id}/end-task/`)
  },

  // Attachment endpoints using REST API custom actions
  attachments: {
    list(taskId: number) {
      return apiClient.get<Attachment[]>(`/qualifications/specialtasks/${taskId}/attachments/`)
    },
    upload(taskId: number, data: FormData) {
      return apiClient.post<Attachment>(`/qualifications/specialtasks/${taskId}/attachments/`, data, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    },
    delete(taskId: number, attachmentId: number) {
      return apiClient.delete(`/qualifications/specialtasks/${taskId}/attachments/${attachmentId}/`)
    }
  }
}
