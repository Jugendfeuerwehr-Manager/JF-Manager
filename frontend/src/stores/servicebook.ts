/**
 * Servicebook Pinia Store
 * 
 * Manages state for services and attendance records using Composition API pattern
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Service,
  ServiceDetail,
  ServiceFormData,
  ServiceListParams,
  ServiceStatistics,
  AttendanceChartData,
  Attendance,
  AttendanceCreate,
  AttendanceListParams,
  BulkAttendanceUpdate,
  MemberAttendanceParams
} from '@/types/servicebook'
import servicebookApi from '@/api/servicebook'
import { getApiErrorMessage } from '@/utils/apiError'

export const useServicebookStore = defineStore('servicebook', () => {
  // ============================================================================
  // State
  // ============================================================================

  // Services
  const services = ref<Service[]>([])
  const currentService = ref<ServiceDetail | null>(null)
  const servicesLoading = ref(false)
  const servicesError = ref<string | null>(null)
  const servicesTotalCount = ref(0)

  // Attendances
  const attendances = ref<Attendance[]>([])
  const attendancesLoading = ref(false)
  const attendancesError = ref<string | null>(null)
  const attendancesTotalCount = ref(0)

  // Statistics
  const statistics = ref<ServiceStatistics | null>(null)
  const statisticsLoading = ref(false)
  const statisticsError = ref<string | null>(null)

  // Chart Data
  const chartData = ref<AttendanceChartData | null>(null)
  const chartLoading = ref(false)
  const chartError = ref<string | null>(null)

  // ============================================================================
  // Computed
  // ============================================================================

  const hasServices = computed(() => services.value.length > 0)
  const hasCurrentService = computed(() => currentService.value !== null)

  // Recent services (first 5)
  const recentServices = computed(() => services.value.slice(0, 5))

  // Services with events (special occurrences)
  const servicesWithEvents = computed(() => services.value.filter((s) => s.has_events))

  // ============================================================================
  // Actions - Services
  // ============================================================================

  /**
   * Fetch services list with optional filters
   */
  async function fetchServices(params?: ServiceListParams) {
    servicesLoading.value = true
    servicesError.value = null

    try {
      const response = await servicebookApi.services.list(params)
      services.value = response.data.results
      servicesTotalCount.value = response.data.count
      return services.value
    } catch (error) {
      servicesError.value = getApiErrorMessage(error, 'Fehler beim Laden der Dienste')
      throw error
    } finally {
      servicesLoading.value = false
    }
  }

  /**
   * Fetch single service detail
   */
  async function fetchService(id: number) {
    servicesLoading.value = true
    servicesError.value = null

    try {
      const response = await servicebookApi.services.get(id)
      currentService.value = response.data
      return currentService.value
    } catch (error) {
      servicesError.value = getApiErrorMessage(error, 'Fehler beim Laden des Dienstes')
      throw error
    } finally {
      servicesLoading.value = false
    }
  }

  /**
   * Create new service
   */
  async function createService(data: ServiceFormData) {
    servicesLoading.value = true
    servicesError.value = null

    try {
      const response = await servicebookApi.services.create(data)
      // Add to local state
      const newService: Service = {
        id: response.data.id,
        start: response.data.start,
        end: response.data.end,
        place: response.data.place,
        topic: response.data.topic,
        department: response.data.department,
        training_session: response.data.training_session,
        operations_manager: response.data.operations_manager,
        attendance_summary: response.data.attendance_summary,
        has_events: response.data.has_events
      }
      services.value.unshift(newService)
      servicesTotalCount.value++
      return response.data
    } catch (error) {
      servicesError.value = getApiErrorMessage(error, 'Fehler beim Erstellen des Dienstes')
      throw error
    } finally {
      servicesLoading.value = false
    }
  }

  /**
   * Update existing service
   */
  async function updateService(id: number, data: ServiceFormData) {
    servicesLoading.value = true
    servicesError.value = null

    try {
      const response = await servicebookApi.services.update(id, data)
      
      // Update in local state
      const index = services.value.findIndex((s) => s.id === id)
      if (index !== -1) {
        services.value[index] = {
          id: response.data.id,
          start: response.data.start,
          end: response.data.end,
          place: response.data.place,
          topic: response.data.topic,
          department: response.data.department,
          training_session: response.data.training_session,
          operations_manager: response.data.operations_manager,
          attendance_summary: response.data.attendance_summary,
          has_events: response.data.has_events
        }
      }
      
      // Update current service if it's the one being edited
      if (currentService.value?.id === id) {
        currentService.value = response.data
      }
      
      return response.data
    } catch (error) {
      servicesError.value =
        getApiErrorMessage(error, 'Fehler beim Aktualisieren des Dienstes')
      throw error
    } finally {
      servicesLoading.value = false
    }
  }

  /**
   * Partially update service
   */
  async function partialUpdateService(id: number, data: Partial<ServiceFormData>) {
    servicesLoading.value = true
    servicesError.value = null

    try {
      const response = await servicebookApi.services.partialUpdate(id, data)
      
      // Update in local state
      const index = services.value.findIndex((s) => s.id === id)
      if (index !== -1) {
        services.value[index] = {
          id: response.data.id,
          start: response.data.start,
          end: response.data.end,
          place: response.data.place,
          topic: response.data.topic,
          department: response.data.department,
          training_session: response.data.training_session,
          operations_manager: response.data.operations_manager,
          attendance_summary: response.data.attendance_summary,
          has_events: response.data.has_events
        }
      }
      
      if (currentService.value?.id === id) {
        currentService.value = response.data
      }
      
      return response.data
    } catch (error) {
      servicesError.value =
        getApiErrorMessage(error, 'Fehler beim Aktualisieren des Dienstes')
      throw error
    } finally {
      servicesLoading.value = false
    }
  }

  /**
   * Delete service
   */
  async function deleteService(id: number) {
    servicesLoading.value = true
    servicesError.value = null

    try {
      await servicebookApi.services.delete(id)
      
      // Remove from local state
      services.value = services.value.filter((s) => s.id !== id)
      servicesTotalCount.value--
      
      if (currentService.value?.id === id) {
        currentService.value = null
      }
    } catch (error) {
      servicesError.value = getApiErrorMessage(error, 'Fehler beim Löschen des Dienstes')
      throw error
    } finally {
      servicesLoading.value = false
    }
  }

  // ============================================================================
  // Actions - Statistics
  // ============================================================================

  /**
   * Fetch servicebook statistics
   */
  async function fetchStatistics() {
    statisticsLoading.value = true
    statisticsError.value = null

    try {
      const response = await servicebookApi.services.getStatistics()
      statistics.value = response.data
      return statistics.value
    } catch (error) {
      statisticsError.value =
        getApiErrorMessage(error, 'Fehler beim Laden der Statistiken')
      throw error
    } finally {
      statisticsLoading.value = false
    }
  }

  /**
   * Fetch attendance chart data
   */
  async function fetchChartData() {
    chartLoading.value = true
    chartError.value = null

    try {
      const response = await servicebookApi.services.getAttendanceChart()
      chartData.value = response.data
      return chartData.value
    } catch (error) {
      chartError.value = getApiErrorMessage(error, 'Fehler beim Laden der Diagrammdaten')
      throw error
    } finally {
      chartLoading.value = false
    }
  }

  // ============================================================================
  // Actions - Attendance
  // ============================================================================

  /**
   * Fetch attendance records
   */
  async function fetchAttendances(params?: AttendanceListParams) {
    attendancesLoading.value = true
    attendancesError.value = null

    try {
      const response = await servicebookApi.attendance.list(params)
      attendances.value = response.data.results
      attendancesTotalCount.value = response.data.count
      return attendances.value
    } catch (error) {
      attendancesError.value =
        getApiErrorMessage(error, 'Fehler beim Laden der Anwesenheiten')
      throw error
    } finally {
      attendancesLoading.value = false
    }
  }

  /**
   * Create attendance record
   */
  async function createAttendance(data: AttendanceCreate) {
    attendancesError.value = null

    try {
      const response = await servicebookApi.attendance.create(data)
      attendances.value.unshift(response.data)
      attendancesTotalCount.value++
      
      // Refresh current service if attendance was created for it
      if (currentService.value?.id === data.service) {
        await fetchService(data.service)
      }
      
      return response.data
    } catch (error) {
      attendancesError.value =
        getApiErrorMessage(error, 'Fehler beim Erstellen der Anwesenheit')
      throw error
    }
  }

  /**
   * Bulk update attendance records for a service
   */
  async function bulkUpdateAttendance(data: BulkAttendanceUpdate) {
    attendancesError.value = null

    console.log('Store: bulkUpdateAttendance called with', data)

    try {
      const response = await servicebookApi.attendance.bulkUpdate(data)
      console.log('Store: API response', response.data)
      
      // Refresh current service to get updated attendance
      if (currentService.value?.id === data.service) {
        console.log('Store: Refreshing current service', data.service)
        await fetchService(data.service)
      }
      
      // Refresh services list to update attendance summaries
      const index = services.value.findIndex((s) => s.id === data.service)
      if (index !== -1) {
        console.log('Store: Refreshing service in list at index', index)
        const updatedService = await servicebookApi.services.get(data.service)
        services.value[index] = {
          id: updatedService.data.id,
          start: updatedService.data.start,
          end: updatedService.data.end,
          place: updatedService.data.place,
          topic: updatedService.data.topic,
          department: updatedService.data.department,
          training_session: updatedService.data.training_session,
          operations_manager: updatedService.data.operations_manager,
          attendance_summary: updatedService.data.attendance_summary,
          has_events: updatedService.data.has_events
        }
      }
      
      console.log('Store: bulkUpdateAttendance complete')
      return response.data
    } catch (error) {
      attendancesError.value =
        getApiErrorMessage(error, 'Fehler beim Aktualisieren der Anwesenheiten')
      throw error
    }
  }

  /**
   * Get attendance for specific member
   */
  async function fetchMemberAttendance(params: MemberAttendanceParams) {
    attendancesLoading.value = true
    attendancesError.value = null

    try {
      const response = await servicebookApi.attendance.getByMember(params)
      return response.data
    } catch (error) {
      attendancesError.value =
        getApiErrorMessage(error, 'Fehler beim Laden der Mitglieder-Anwesenheiten')
      throw error
    } finally {
      attendancesLoading.value = false
    }
  }

  // ============================================================================
  // Utility Actions
  // ============================================================================

  /**
   * Clear current service
   */
  function clearCurrentService() {
    currentService.value = null
  }

  /**
   * Reset all state
   */
  function resetState() {
    services.value = []
    currentService.value = null
    servicesLoading.value = false
    servicesError.value = null
    servicesTotalCount.value = 0

    attendances.value = []
    attendancesLoading.value = false
    attendancesError.value = null
    attendancesTotalCount.value = 0

    statistics.value = null
    statisticsLoading.value = false
    statisticsError.value = null

    chartData.value = null
    chartLoading.value = false
    chartError.value = null
  }

  // ============================================================================
  // Return Store
  // ============================================================================

  return {
    // State
    services,
    currentService,
    servicesLoading,
    servicesError,
    servicesTotalCount,
    attendances,
    attendancesLoading,
    attendancesError,
    attendancesTotalCount,
    statistics,
    statisticsLoading,
    statisticsError,
    chartData,
    chartLoading,
    chartError,

    // Computed
    hasServices,
    hasCurrentService,
    recentServices,
    servicesWithEvents,

    // Actions
    fetchServices,
    fetchService,
    createService,
    updateService,
    partialUpdateService,
    deleteService,
    fetchStatistics,
    fetchChartData,
    fetchAttendances,
    createAttendance,
    bulkUpdateAttendance,
    fetchMemberAttendance,
    clearCurrentService,
    resetState
  }
})
