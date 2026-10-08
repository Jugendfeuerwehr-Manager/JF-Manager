/**
 * PART-02: mobile overview and registrations of the servicebook.
 * Attendance writes are not handled here; they stay in the attendance board API.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { servicesApi } from '@/api/servicebook'
import type {
  ApplyExcusedPreview,
  ServiceOverview,
  ServiceRegistrations,
} from '@/types/servicebook'
import { classifyApiError, type ApiErrorKind } from '@/utils/apiError'

export const useServiceRegistrationsStore = defineStore('serviceRegistrations', () => {
  const overview = ref<ServiceOverview>({ today: [], upcoming: [], open: [] })
  const overviewLoading = ref(false)
  const overviewError = ref<ApiErrorKind | null>(null)

  const registrations = ref<ServiceRegistrations | null>(null)
  const registrationsLoading = ref(false)
  const registrationsError = ref<ApiErrorKind | null>(null)

  async function fetchOverview(department?: number | null) {
    overviewLoading.value = true
    overviewError.value = null
    try {
      overview.value = (await servicesApi.getOverview({ department })).data
    } catch (error) {
      overviewError.value = classifyApiError(error)
    } finally {
      overviewLoading.value = false
    }
  }

  /** Quiet refreshes keep the current data on screen when polling fails. */
  async function fetchRegistrations(serviceId: number, quiet = false) {
    if (!quiet) registrationsLoading.value = true
    registrationsError.value = null
    try {
      registrations.value = (await servicesApi.getRegistrations(serviceId)).data
    } catch (error) {
      registrationsError.value = classifyApiError(error)
      if (!quiet) registrations.value = null
    } finally {
      registrationsLoading.value = false
    }
  }

  function previewExcused(serviceId: number) {
    return servicesApi.applyExcused(serviceId, { dry_run: true }).then((r) => r.data)
  }

  function applyExcused(serviceId: number, memberIds: number[]): Promise<ApplyExcusedPreview> {
    return servicesApi
      .applyExcused(serviceId, { dry_run: false, member_ids: memberIds })
      .then((r) => r.data)
  }

  function reset() {
    registrations.value = null
    registrationsError.value = null
  }

  return {
    overview, overviewLoading, overviewError,
    registrations, registrationsLoading, registrationsError,
    fetchOverview, fetchRegistrations, previewExcused, applyExcused, reset,
  }
})
