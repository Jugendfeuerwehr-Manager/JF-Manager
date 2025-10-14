/**
 * Servicebook API Client
 * 
 * HTTP client for servicebook endpoints (services and attendance)
 */

import apiClient from './index'
import type {
  Service,
  ServiceDetail,
  ServiceFormData,
  ServiceListParams,
  ServiceStatistics,
  AttendanceChartData,
  ServiceAttendanceSummaryResponse,
  Attendance,
  AttendanceCreate,
  AttendanceListParams,
  BulkAttendanceUpdate,
  BulkAttendanceUpdateResult,
  MemberAttendanceParams,
  MemberAttendanceResponse,
  PaginatedResponse
} from '@/types/servicebook'

/**
 * Services API
 */
export const servicesApi = {
  /**
   * List services with optional filtering and pagination
   */
  list(params?: ServiceListParams) {
    return apiClient.get<PaginatedResponse<Service>>('/servicebook/services/', { params })
  },

  /**
   * Get single service detail
   */
  get(id: number) {
    return apiClient.get<ServiceDetail>(`/servicebook/services/${id}/`)
  },

  /**
   * Create new service
   */
  create(data: ServiceFormData) {
    return apiClient.post<ServiceDetail>('/servicebook/services/', data)
  },

  /**
   * Update existing service (full update)
   */
  update(id: number, data: ServiceFormData) {
    return apiClient.put<ServiceDetail>(`/servicebook/services/${id}/`, data)
  },

  /**
   * Partially update service
   */
  partialUpdate(id: number, data: Partial<ServiceFormData>) {
    return apiClient.patch<ServiceDetail>(`/servicebook/services/${id}/`, data)
  },

  /**
   * Delete service
   */
  delete(id: number) {
    return apiClient.delete(`/servicebook/services/${id}/`)
  },

  /**
   * Get servicebook statistics (total services, top lists, etc.)
   */
  getStatistics() {
    return apiClient.get<ServiceStatistics>('/servicebook/services/statistics/')
  },

  /**
   * Get attendance chart data for visualization
   */
  getAttendanceChart() {
    return apiClient.get<AttendanceChartData>('/servicebook/services/attendance_chart/')
  },

  /**
   * Get attendance summary for a specific service
   */
  getAttendanceSummary(id: number) {
    return apiClient.get<ServiceAttendanceSummaryResponse>(
      `/servicebook/services/${id}/attendance_summary/`
    )
  }
}

/**
 * Attendance API
 */
export const attendanceApi = {
  /**
   * List attendance records with optional filtering
   */
  list(params?: AttendanceListParams) {
    return apiClient.get<PaginatedResponse<Attendance>>('/servicebook/attendances/', { params })
  },

  /**
   * Get single attendance record
   */
  get(id: number) {
    return apiClient.get<Attendance>(`/servicebook/attendances/${id}/`)
  },

  /**
   * Create new attendance record
   */
  create(data: AttendanceCreate) {
    return apiClient.post<Attendance>('/servicebook/attendances/', data)
  },

  /**
   * Update attendance record (full update)
   */
  update(id: number, data: AttendanceCreate) {
    return apiClient.put<Attendance>(`/servicebook/attendances/${id}/`, data)
  },

  /**
   * Partially update attendance record
   */
  partialUpdate(id: number, data: Partial<AttendanceCreate>) {
    return apiClient.patch<Attendance>(`/servicebook/attendances/${id}/`, data)
  },

  /**
   * Delete attendance record
   */
  delete(id: number) {
    return apiClient.delete(`/servicebook/attendances/${id}/`)
  },

  /**
   * Bulk update or create attendance records for a service
   * This is the most efficient way to mark attendance for multiple members
   */
  bulkUpdate(data: BulkAttendanceUpdate) {
    return apiClient.post<BulkAttendanceUpdateResult>(
      '/servicebook/attendances/bulk_update/',
      data
    )
  },

  /**
   * Get attendance records for a specific member
   */
  getByMember(params: MemberAttendanceParams) {
    return apiClient.get<MemberAttendanceResponse>('/servicebook/attendances/by_member/', {
      params
    })
  }
}

/**
 * Combined servicebook API export
 */
export const servicebookApi = {
  services: servicesApi,
  attendance: attendanceApi
}

export default servicebookApi
