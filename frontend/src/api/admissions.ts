/**
 * Admissions API – application forms and text blocks. Only HTTP, no logic.
 */
import apiClient from './index'
import type {
  AdmissionForm,
  AdmissionFormCreate,
  AdmissionFormPage,
  AdmissionFormUpdate,
  AdmissionFormVersion,
  AdmissionTextBlock,
  AdmissionTextBlockPage,
  BuilderReferences
} from '@/types/admissions'

export const admissionFormsApi = {
  list: (params?: { department?: number; is_active?: boolean; limit?: number }) =>
    apiClient.get<AdmissionFormPage>('/admissions/forms/', { params }),
  get: (id: number) => apiClient.get<AdmissionForm>(`/admissions/forms/${id}/`),
  create: (data: AdmissionFormCreate) => apiClient.post<AdmissionForm>('/admissions/forms/', data),
  update: (id: number, data: AdmissionFormUpdate) => apiClient.patch<AdmissionForm>(`/admissions/forms/${id}/`, data),
  remove: (id: number) => apiClient.delete(`/admissions/forms/${id}/`),
  publish: (id: number, changeNote = '') =>
    apiClient.post<AdmissionFormVersion>(`/admissions/forms/${id}/publish/`, { change_note: changeNote }),
  versions: (id: number) => apiClient.get<AdmissionFormVersion[]>(`/admissions/forms/${id}/versions/`),
  references: () => apiClient.get<BuilderReferences>('/admissions/forms/references/')
}

export const admissionTextBlocksApi = {
  list: () => apiClient.get<AdmissionTextBlockPage>('/admissions/text-blocks/', { params: { limit: 200 } }),
  create: (data: Pick<AdmissionTextBlock, 'title' | 'body' | 'department'>) =>
    apiClient.post<AdmissionTextBlock>('/admissions/text-blocks/', data),
  update: (id: number, data: Partial<Pick<AdmissionTextBlock, 'title' | 'body'>>) =>
    apiClient.patch<AdmissionTextBlock>(`/admissions/text-blocks/${id}/`, data),
  remove: (id: number) => apiClient.delete(`/admissions/text-blocks/${id}/`)
}
