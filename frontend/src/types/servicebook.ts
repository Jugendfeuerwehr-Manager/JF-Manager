/**
 * Servicebook TypeScript Type Definitions
 *
 * Models for managing services (Dienste) and attendance tracking
 */

// ============================================================================
// Enums and Constants
// ============================================================================

/**
 * Attendance state enum matching Django model choices
 */
export enum AttendanceState {
  PRESENT = 'A', // Anwesend
  EXCUSED = 'E', // Entschuldigt
  ABSENT = 'F', // Fehlend
}

/**
 * Human-readable labels for attendance states
 */
export const AttendanceStateLabels: Record<AttendanceState, string> = {
  [AttendanceState.PRESENT]: 'Anwesend',
  [AttendanceState.EXCUSED]: 'Entschuldigt',
  [AttendanceState.ABSENT]: 'Fehlend',
}

/**
 * Color mappings for attendance states (PrimeVue severity)
 */
export const AttendanceStateColors: Record<AttendanceState, string> = {
  [AttendanceState.PRESENT]: 'success',
  [AttendanceState.EXCUSED]: 'warn',
  [AttendanceState.ABSENT]: 'danger',
}

// ============================================================================
// Core Models
// ============================================================================

/**
 * Operations Manager (simplified user model)
 */
export interface OperationsManager {
  id: number
  username: string
  full_name: string
  email: string
}

/**
 * Attendance Summary Statistics
 */
export interface AttendanceSummary {
  present: number
  excused: number
  absent: number
  total: number
}

/**
 * Service List Item (lightweight for list views)
 */
export interface Service {
  id: number
  start: string // ISO datetime
  end: string // ISO datetime
  place: string | null
  topic: string | null
  department?: number | null
  training_status?: import('./training').TrainingStatus | null
  training_session?: number | null
  operations_manager: OperationsManager[]
  attendance_summary: AttendanceSummary
  has_events: boolean
}

/**
 * Attendee with Status (for service detail view)
 */
export interface AttendeeWithStatus {
  id: number
  name: string
  lastname: string
  full_name: string
  state: AttendanceState | null
  attendance_id?: number
}

/**
 * Service Detail (full information including attendees)
 */
export interface ServiceDetail {
  id: number
  start: string
  end: string
  place: string | null
  topic: string | null
  description: string | null
  events: string | null // Special occurrences
  department?: number | null
  training_status?: import('./training').TrainingStatus | null
  training_session?: number | null
  operations_manager: OperationsManager[]
  attendance_summary: AttendanceSummary
  attendees_with_status: AttendeeWithStatus[]
  has_events: boolean
  duration_minutes: number | null
}

/**
 * Service Create/Update Payload
 */
export interface ServiceFormData {
  start: string
  end: string
  place?: string
  topic?: string
  description?: string
  events?: string
  operations_manager_ids?: number[]
}

/**
 * Attendance Record
 */
export interface Attendance {
  id: number
  person: number
  person_name: string
  person_details: {
    id: number
    name: string
    lastname: string
    full_name: string
  } | null
  service: number
  service_topic: string | null
  service_date: string
  state: AttendanceState | null
  state_display: string
}

/**
 * Attendance Create Payload
 */
export interface AttendanceCreate {
  person: number
  service: number
  state: AttendanceState
}

/**
 * Bulk Attendance Update Item
 */
export interface BulkAttendanceItem {
  person_id: number
  state: AttendanceState | null
}

/**
 * Bulk Attendance Update Payload
 */
export interface BulkAttendanceUpdate {
  service: number
  attendances: BulkAttendanceItem[]
}

/**
 * Bulk Attendance Update Response
 */
export interface BulkAttendanceUpdateResult {
  created: number
  updated: number
  total: number
}

// ============================================================================
// Statistics & Charts
// ============================================================================

/**
 * Attendance Chart Data (for visualization)
 */
export interface AttendanceChartData {
  service_labels: string[]
  service_dates: string[]
  attendance_data: {
    A: number[] // Present
    E: number[] // Excused
    F: number[] // Absent
  }
}

/**
 * Service Attendance Summary (detailed endpoint response)
 */
export interface ServiceAttendanceSummaryResponse {
  summary: AttendanceSummary
  attendees: AttendeeWithStatus[]
}

// ============================================================================
// API Response Types
// ============================================================================

/**
 * Paginated Response for Services
 */
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ============================================================================
// Filter & Query Types
// ============================================================================

/**
 * Service List Query Parameters
 */
export interface ServiceListParams {
  limit?: number
  offset?: number
  ordering?: string
  search?: string
  topic?: string
  place?: string
  operations_manager?: number
  start?: string
  end?: string
  start__gte?: string
  start__lte?: string
  end__gte?: string
  end__lte?: string
}

/**
 * Attendance List Query Parameters
 */
export interface AttendanceListParams {
  page?: number
  page_size?: number
  ordering?: string
  search?: string
  person?: number
  service?: number
  state?: AttendanceState
}

/**
 * Member Attendance Query Parameters
 */
export interface MemberAttendanceParams {
  member_id: number
  limit?: number
}

/**
 * Member Attendance Response
 */
export interface MemberAttendanceResponse {
  attendances: Attendance[]
  summary: AttendanceSummary
}

// ============================================================================
// UI Helper Types
// ============================================================================

/**
 * Service Filter Form Data
 */
export interface ServiceFilters {
  search?: string
  topic?: string
  place?: string
  operations_manager?: number
  dateFrom?: Date | null
  dateTo?: Date | null
}

/**
 * Attendance Button State (for UI)
 */
export interface AttendanceButtonState {
  memberId: number
  currentState: AttendanceState | null
  loading: boolean
  error: string | null
}

export interface AttendanceBoardPerson {
  id: number
  full_name: string
  state: AttendanceState | null
}

export interface AttendanceBoard {
  members: AttendanceBoardPerson[]
  staff: AttendanceBoardPerson[]
}

export type AttendanceWarning = 'low_rate' | 'declining' | 'missed_in_a_row'

export interface AttendanceCounts {
  present: number
  excused: number
  absent: number
  recorded: number
}

/** One person in the attendance evaluation; rates are percent of recorded entries. */
export interface AttendanceReportPerson extends AttendanceCounts {
  id: number
  full_name: string
  rate: number | null
  hours: number
  /** Rate per month, aligned with the group's months; null without entries. */
  months: (number | null)[]
  trend: { previous: number; recent: number; delta: number } | null
  missed_in_a_row: number
  warnings: AttendanceWarning[]
}

export interface AttendanceReportGroup {
  summary: AttendanceCounts & { rate: number | null; people: number; with_warnings: number }
  months: (AttendanceCounts & { month: string; rate: number | null })[]
  people: AttendanceReportPerson[]
}

export interface AttendanceReport {
  period: { date_from: string; date_to: string }
  services: { count: number; hours: number }
  thresholds: { low_rate: number; low_rate_min_records: number; decline_points: number; missed_in_a_row: number }
  members: AttendanceReportGroup
  staff: AttendanceReportGroup
}
