/**
 * Membership movements API – only HTTP, no logic.
 */
import apiClient from './index'
import type { PaginatedResponse } from '@/types/common'
import type {
  AnnualReportResponse,
  MembershipEvent,
  MembershipEventCorrection,
  MembershipEventListParams,
  MembershipEventPage,
  ReportManual,
  StatisticsProfile
} from '@/types/membership'

export const membershipApi = {
  listEvents: (params?: MembershipEventListParams) =>
    apiClient.get<MembershipEventPage>('/membership/events/', { params }),

  correctEvent: (id: number, data: MembershipEventCorrection) =>
    apiClient.patch<MembershipEvent>(`/membership/events/${id}/`, data)
}

export const annualReportApi = {
  preview: (department: number, year: number) =>
    apiClient.get<AnnualReportResponse>('/membership/annual-reports/preview/', { params: { department, year } }),
  saveManual: (department: number, year: number, manual: ReportManual) =>
    apiClient.post<AnnualReportResponse>('/membership/annual-reports/manual/', { department, year, ...manual }),
  finalize: (department: number, year: number) =>
    apiClient.post<AnnualReportResponse>('/membership/annual-reports/finalize/', { department, year }),
  exportXlsx: (department: number, year: number) =>
    apiClient.get<Blob>('/membership/annual-reports/export/', { params: { department, year }, responseType: 'blob' }),
  profiles: (department: number) =>
    apiClient.get<PaginatedResponse<StatisticsProfile>>('/membership/statistics-profiles/', { params: { department } }),
  createProfile: (data: Omit<StatisticsProfile, 'id'>) =>
    apiClient.post<StatisticsProfile>('/membership/statistics-profiles/', data),
  updateProfile: (id: number, data: Partial<Omit<StatisticsProfile, 'id' | 'department'>>) =>
    apiClient.patch<StatisticsProfile>(`/membership/statistics-profiles/${id}/`, data)
}
