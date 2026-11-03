/**
 * Admissions API – application forms and text blocks. Only HTTP, no logic.
 */
import apiClient from './index'
import type { PaginatedResponse } from '@/types/common'
import type {
  AdmissionForm,
  AdmissionFormCreate,
  AdmissionFormPage,
  AdmissionFormUpdate,
  AdmissionFormVersion,
  AdmissionTextBlock,
  AdmissionTextBlockPage,
  AdmissionVoucher,
  ApplicationDetail,
  ApplicationExport,
  ApplicationListItem,
  ApplicationStatus,
  ApplicationVerification,
  BuilderReferences,
  CommitteeMeeting,
  CreatedVoucher,
  DecisionInput,
  ParentSuggestion,
  PublicAdmissionForm,
  PublicSealCheck,
  PublicSubmitResult,
  TakeOverInput,
  VoucherCreate
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

export const admissionVouchersApi = {
  list: (params?: { form?: number; limit?: number }) =>
    apiClient.get<PaginatedResponse<AdmissionVoucher>>('/admissions/vouchers/', { params }),
  create: (data: VoucherCreate) => apiClient.post<CreatedVoucher>('/admissions/vouchers/', data),
  revoke: (id: number) => apiClient.post<AdmissionVoucher>(`/admissions/vouchers/${id}/revoke/`)
}

export const applicationsApi = {
  list: (params?: { status?: ApplicationStatus; department?: number; limit?: number; search?: string }) =>
    apiClient.get<PaginatedResponse<ApplicationListItem>>('/admissions/applications/', { params }),
  get: (id: number) => apiClient.get<ApplicationDetail>(`/admissions/applications/${id}/`),
  verify: (id: number) => apiClient.get<ApplicationVerification>(`/admissions/applications/${id}/verify/`),
  parentSuggestions: (id: number) =>
    apiClient.get<ParentSuggestion[][]>(`/admissions/applications/${id}/parent-suggestions/`),
  decide: (id: number, data: DecisionInput) =>
    apiClient.post<ApplicationDetail>(`/admissions/applications/${id}/decide/`, data),
  takeOver: (id: number, data: TakeOverInput) =>
    apiClient.post<{ member: number }>(`/admissions/applications/${id}/take-over/`, data),
  exportSealed: (id: number) => apiClient.get<ApplicationExport>(`/admissions/applications/${id}/export/`)
}

export const meetingsApi = {
  list: (params?: { department?: number; limit?: number }) =>
    apiClient.get<PaginatedResponse<CommitteeMeeting>>('/admissions/meetings/', { params }),
  create: (data: Pick<CommitteeMeeting, 'department' | 'body' | 'date' | 'protocol_ref' | 'note'>) =>
    apiClient.post<CommitteeMeeting>('/admissions/meetings/', data),
  decide: (id: number, data: DecisionInput & { applications: number[] }) =>
    apiClient.post<{ decided: number[] }>(`/admissions/meetings/${id}/decide/`, data)
}

/** Public endpoints: the voucher code goes in a header, never in the URL. */
export const publicAdmissionApi = {
  form: (code: string) =>
    apiClient.get<PublicAdmissionForm>('/public/admissions/', { headers: { 'X-Admission-Code': code } }),
  submit: (code: string, answers: Record<string, unknown>) =>
    apiClient.post<PublicSubmitResult>('/public/admissions/', { answers }, { headers: { 'X-Admission-Code': code } }),
  verify: (publicId: string) => apiClient.get<PublicSealCheck>(`/public/admissions/verify/${encodeURIComponent(publicId)}/`)
}
