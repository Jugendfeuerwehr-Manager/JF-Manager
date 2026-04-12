/**
 * Pinia store for Qualifications & Special Tasks
 * Follows Composition API pattern from stores/orders.ts
 * ALL business logic is encapsulated here
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  qualificationsApi,
  qualificationTypesApi,
  specialTasksApi,
  specialTaskTypesApi
} from '@/api/qualifications'
import type {
  Qualification,
  QualificationType,
  SpecialTask,
  SpecialTaskType,
  QualificationListParams,
  SpecialTaskListParams,
  QualificationStatistics,
  QualificationCreate,
  QualificationUpdate,
  SpecialTaskCreate,
  SpecialTaskUpdate,
  QualificationTypeCreate,
  SpecialTaskTypeCreate,
  Attachment
} from '@/types/qualifications'
import { getApiErrorMessage } from '@/utils/apiError'

export const useQualificationsStore = defineStore('qualifications', () => {
  // ==================== STATE ====================

  // Qualifications
  const qualifications = ref<Qualification[]>([])
  const currentQualification = ref<Qualification | null>(null)
  const qualificationsTotal = ref(0)
  const qualificationsPage = ref(1)
  const qualificationsPageSize = ref(20)

  // Qualification Types
  const qualificationTypes = ref<QualificationType[]>([])
  const qualificationTypesLoaded = ref(false)

  // Special Tasks
  const specialTasks = ref<SpecialTask[]>([])
  const currentSpecialTask = ref<SpecialTask | null>(null)
  const specialTasksTotal = ref(0)
  const specialTasksPage = ref(1)
  const specialTasksPageSize = ref(20)

  // Special Task Types
  const specialTaskTypes = ref<SpecialTaskType[]>([])
  const specialTaskTypesLoaded = ref(false)

  // Statistics
  const statistics = ref<QualificationStatistics | null>(null)
  const qualificationAttachments = ref<Record<number, Attachment[]>>({})
  const specialTaskAttachments = ref<Record<number, Attachment[]>>({})

  // Loading states
  const loading = ref(false)
  const loadingDetail = ref(false)
  const loadingStatistics = ref(false)
  const loadingTypes = ref(false)
  const loadingAttachments = ref(false)

  // Error states
  const error = ref<string | null>(null)

  // ==================== COMPUTED ====================

  const hasQualifications = computed(() => qualifications.value.length > 0)
  const hasSpecialTasks = computed(() => specialTasks.value.length > 0)

  const expiredQualifications = computed(() =>
    qualifications.value.filter((q) => q.is_expired)
  )

  const expiringQualifications = computed(() =>
    qualifications.value.filter((q) => q.expires_soon && !q.is_expired)
  )

  const activeQualifications = computed(() =>
    qualifications.value.filter((q) => !q.is_expired)
  )

  const activeSpecialTasks = computed(() => specialTasks.value.filter((t) => t.is_active))

  const endedSpecialTasks = computed(() => specialTasks.value.filter((t) => !t.is_active))

  const qualificationTypesOptions = computed(() =>
    qualificationTypes.value.map((type) => ({
      label: type.name,
      value: type.id
    }))
  )

  const specialTaskTypesOptions = computed(() =>
    specialTaskTypes.value.map((type) => ({
      label: type.name,
      value: type.id
    }))
  )

  // ==================== ACTIONS - Qualifications ====================

  async function fetchQualifications(params?: QualificationListParams) {
    loading.value = true
    error.value = null

    try {
      const response = await qualificationsApi.list(params)
      qualifications.value = response.data.results // CRITICAL: Extract .results!
      qualificationsTotal.value = response.data.count

      if (params?.page) {
        qualificationsPage.value = params.page
      }

      return qualifications.value
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to fetch qualifications')
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchQualification(id: number) {
    loadingDetail.value = true
    error.value = null

    try {
      const response = await qualificationsApi.get(id)
      currentQualification.value = response.data
      return currentQualification.value
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to fetch qualification')
      throw e
    } finally {
      loadingDetail.value = false
    }
  }

  async function createQualification(data: QualificationCreate) {
    loading.value = true
    error.value = null

    try {
      const response = await qualificationsApi.create(data)

      // Add to list if on first page
      if (qualificationsPage.value === 1) {
        qualifications.value.unshift(response.data)
      }

      qualificationsTotal.value++

      return response.data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to create qualification')
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateQualification(id: number, data: QualificationUpdate) {
    loading.value = true
    error.value = null

    try {
      const response = await qualificationsApi.update(id, data)

      // Update in list
      const index = qualifications.value.findIndex((q) => q.id === id)
      if (index !== -1) {
        qualifications.value[index] = response.data
      }

      // Update current if it's the same
      if (currentQualification.value?.id === id) {
        currentQualification.value = response.data
      }

      return response.data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to update qualification')
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteQualification(id: number) {
    loading.value = true
    error.value = null

    try {
      await qualificationsApi.delete(id)

      // Remove from list
      qualifications.value = qualifications.value.filter((q) => q.id !== id)
      qualificationsTotal.value--

      // Clear current if it's the same
      if (currentQualification.value?.id === id) {
        currentQualification.value = null
      }
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to delete qualification')
      throw e
    } finally {
      loading.value = false
    }
  }

  async function calculateExpiry(typeId: number, dateAcquired: string) {
    try {
      const response = await qualificationsApi.calculateExpiry({
        type_id: typeId,
        date_acquired: dateAcquired
      })
      return response.data.date_expires
    } catch (e) {
      console.error('Failed to calculate expiry:', e)
      return null
    }
  }

  // ==================== ACTIONS - Qualification Types ====================

  async function fetchQualificationTypes(forceRefresh = false) {
    if (qualificationTypesLoaded.value && !forceRefresh) {
      return qualificationTypes.value
    }

    loadingTypes.value = true

    try {
      const response = await qualificationTypesApi.list()
      qualificationTypes.value = response.data.results // Extract .results!
      qualificationTypesLoaded.value = true
      return qualificationTypes.value
    } catch (e) {
      error.value =
        getApiErrorMessage(e, 'Failed to fetch qualification types')
      throw e
    } finally {
      loadingTypes.value = false
    }
  }

  async function createQualificationType(data: QualificationTypeCreate) {
    loadingTypes.value = true

    try {
      const response = await qualificationTypesApi.create(data)
      qualificationTypes.value.push(response.data)
      return response.data
    } catch (e) {
      error.value =
        getApiErrorMessage(e, 'Failed to create qualification type')
      throw e
    } finally {
      loadingTypes.value = false
    }
  }

  async function updateQualificationType(id: number, data: Partial<QualificationTypeCreate>) {
    loadingTypes.value = true

    try {
      const response = await qualificationTypesApi.update(id, data)
      const index = qualificationTypes.value.findIndex((t) => t.id === id)
      if (index !== -1) {
        qualificationTypes.value[index] = response.data
      }
      return response.data
    } catch (e) {
      error.value =
        getApiErrorMessage(e, 'Failed to update qualification type')
      throw e
    } finally {
      loadingTypes.value = false
    }
  }

  async function deleteQualificationType(id: number) {
    loadingTypes.value = true

    try {
      await qualificationTypesApi.delete(id)
      qualificationTypes.value = qualificationTypes.value.filter((t) => t.id !== id)
    } catch (e) {
      error.value =
        getApiErrorMessage(e, 'Failed to delete qualification type')
      throw e
    } finally {
      loadingTypes.value = false
    }
  }

  // ==================== ACTIONS - Special Tasks ====================

  async function fetchSpecialTasks(params?: SpecialTaskListParams) {
    loading.value = true
    error.value = null

    try {
      const response = await specialTasksApi.list(params)
      specialTasks.value = response.data.results // Extract .results!
      specialTasksTotal.value = response.data.count

      if (params?.page) {
        specialTasksPage.value = params.page
      }

      return specialTasks.value
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to fetch special tasks')
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchSpecialTask(id: number) {
    loadingDetail.value = true
    error.value = null

    try {
      const response = await specialTasksApi.get(id)
      currentSpecialTask.value = response.data
      return currentSpecialTask.value
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to fetch special task')
      throw e
    } finally {
      loadingDetail.value = false
    }
  }

  async function createSpecialTask(data: SpecialTaskCreate) {
    loading.value = true
    error.value = null

    try {
      const response = await specialTasksApi.create(data)

      if (specialTasksPage.value === 1) {
        specialTasks.value.unshift(response.data)
      }

      specialTasksTotal.value++

      return response.data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to create special task')
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateSpecialTask(id: number, data: SpecialTaskUpdate) {
    loading.value = true
    error.value = null

    try {
      const response = await specialTasksApi.update(id, data)

      const index = specialTasks.value.findIndex((t) => t.id === id)
      if (index !== -1) {
        specialTasks.value[index] = response.data
      }

      if (currentSpecialTask.value?.id === id) {
        currentSpecialTask.value = response.data
      }

      return response.data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to update special task')
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteSpecialTask(id: number) {
    loading.value = true
    error.value = null

    try {
      await specialTasksApi.delete(id)

      specialTasks.value = specialTasks.value.filter((t) => t.id !== id)
      specialTasksTotal.value--

      if (currentSpecialTask.value?.id === id) {
        currentSpecialTask.value = null
      }
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to delete special task')
      throw e
    } finally {
      loading.value = false
    }
  }

  async function endSpecialTask(id: number) {
    loading.value = true
    error.value = null

    try {
      const response = await specialTasksApi.endTask(id)

      // Update in list
      const index = specialTasks.value.findIndex((t) => t.id === id)
      if (index !== -1) {
        specialTasks.value[index] = response.data
      }

      // Update current
      if (currentSpecialTask.value?.id === id) {
        currentSpecialTask.value = response.data
      }

      return response.data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to end special task')
      throw e
    } finally {
      loading.value = false
    }
  }

  // ==================== ACTIONS - Attachments ====================

  async function fetchQualificationAttachments(qualificationId: number) {
    loadingAttachments.value = true
    error.value = null

    try {
      const response = await qualificationsApi.attachments.list(qualificationId)
      qualificationAttachments.value = {
        ...qualificationAttachments.value,
        [qualificationId]: response.data
      }

      if (currentQualification.value?.id === qualificationId) {
        currentQualification.value = {
          ...currentQualification.value,
          attachments: response.data
        }
      }

      return response.data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to load attachments')
      throw e
    } finally {
      loadingAttachments.value = false
    }
  }

  async function uploadQualificationAttachment(qualificationId: number, data: FormData) {
    loadingAttachments.value = true
    error.value = null

    try {
      const response = await qualificationsApi.attachments.upload(qualificationId, data)
      
      // Legacy view returns { success: true, attachment: {...} }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const attachment = ((response.data as any).attachment || response.data) as Attachment

      const existing = qualificationAttachments.value[qualificationId] || []
      qualificationAttachments.value = {
        ...qualificationAttachments.value,
        [qualificationId]: [attachment, ...existing]
      }

      if (currentQualification.value?.id === qualificationId) {
        currentQualification.value = {
          ...currentQualification.value,
          attachments: [attachment, ...(currentQualification.value.attachments || [])]
        }
      }

      return attachment
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to upload attachment')
      throw e
    } finally {
      loadingAttachments.value = false
    }
  }

  async function deleteQualificationAttachment(qualificationId: number, attachmentId: number) {
    loadingAttachments.value = true
    error.value = null

    try {
      await qualificationsApi.attachments.delete(qualificationId, attachmentId)

      const existing = qualificationAttachments.value[qualificationId] || []
      qualificationAttachments.value = {
        ...qualificationAttachments.value,
        [qualificationId]: existing.filter((attachment) => attachment.id !== attachmentId)
      }

      if (currentQualification.value?.id === qualificationId && currentQualification.value.attachments) {
        currentQualification.value = {
          ...currentQualification.value,
          attachments: currentQualification.value.attachments.filter((attachment) => attachment.id !== attachmentId)
        }
      }
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to delete attachment')
      throw e
    } finally {
      loadingAttachments.value = false
    }
  }

  async function fetchSpecialTaskAttachments(taskId: number) {
    loadingAttachments.value = true
    error.value = null

    try {
      const response = await specialTasksApi.attachments.list(taskId)
      specialTaskAttachments.value = {
        ...specialTaskAttachments.value,
        [taskId]: response.data
      }

      if (currentSpecialTask.value?.id === taskId) {
        currentSpecialTask.value = {
          ...currentSpecialTask.value,
          attachments: response.data
        }
      }

      return response.data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to load attachments')
      throw e
    } finally {
      loadingAttachments.value = false
    }
  }

  async function uploadSpecialTaskAttachment(taskId: number, data: FormData) {
    loadingAttachments.value = true
    error.value = null

    try {
      const response = await specialTasksApi.attachments.upload(taskId, data)
      
      // Legacy view returns { success: true, attachment: {...} }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const attachment = ((response.data as any).attachment || response.data) as Attachment

      const existing = specialTaskAttachments.value[taskId] || []
      specialTaskAttachments.value = {
        ...specialTaskAttachments.value,
        [taskId]: [attachment, ...existing]
      }

      if (currentSpecialTask.value?.id === taskId) {
        currentSpecialTask.value = {
          ...currentSpecialTask.value,
          attachments: [attachment, ...(currentSpecialTask.value.attachments || [])]
        }
      }

      return attachment
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to upload attachment')
      throw e
    } finally {
      loadingAttachments.value = false
    }
  }

  async function deleteSpecialTaskAttachment(taskId: number, attachmentId: number) {
    loadingAttachments.value = true
    error.value = null

    try {
      await specialTasksApi.attachments.delete(taskId, attachmentId)

      const existing = specialTaskAttachments.value[taskId] || []
      specialTaskAttachments.value = {
        ...specialTaskAttachments.value,
        [taskId]: existing.filter((attachment) => attachment.id !== attachmentId)
      }

      if (currentSpecialTask.value?.id === taskId && currentSpecialTask.value.attachments) {
        currentSpecialTask.value = {
          ...currentSpecialTask.value,
          attachments: currentSpecialTask.value.attachments.filter((attachment) => attachment.id !== attachmentId)
        }
      }
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to delete attachment')
      throw e
    } finally {
      loadingAttachments.value = false
    }
  }

  // ==================== ACTIONS - Special Task Types ====================

  async function fetchSpecialTaskTypes(forceRefresh = false) {
    if (specialTaskTypesLoaded.value && !forceRefresh) {
      return specialTaskTypes.value
    }

    loadingTypes.value = true

    try {
      const response = await specialTaskTypesApi.list()
      specialTaskTypes.value = response.data.results // Extract .results!
      specialTaskTypesLoaded.value = true
      return specialTaskTypes.value
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to fetch special task types')
      throw e
    } finally {
      loadingTypes.value = false
    }
  }

  async function createSpecialTaskType(data: SpecialTaskTypeCreate) {
    loadingTypes.value = true

    try {
      const response = await specialTaskTypesApi.create(data)
      specialTaskTypes.value.push(response.data)
      return response.data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to create special task type')
      throw e
    } finally {
      loadingTypes.value = false
    }
  }

  async function updateSpecialTaskType(id: number, data: Partial<SpecialTaskTypeCreate>) {
    loadingTypes.value = true

    try {
      const response = await specialTaskTypesApi.update(id, data)
      const index = specialTaskTypes.value.findIndex((t) => t.id === id)
      if (index !== -1) {
        specialTaskTypes.value[index] = response.data
      }
      return response.data
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to update special task type')
      throw e
    } finally {
      loadingTypes.value = false
    }
  }

  async function deleteSpecialTaskType(id: number) {
    loadingTypes.value = true

    try {
      await specialTaskTypesApi.delete(id)
      specialTaskTypes.value = specialTaskTypes.value.filter((t) => t.id !== id)
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to delete special task type')
      throw e
    } finally {
      loadingTypes.value = false
    }
  }

  // ==================== ACTIONS - Statistics ====================

  async function fetchStatistics() {
    loadingStatistics.value = true
    error.value = null

    try {
      const response = await qualificationsApi.statistics()
      statistics.value = response.data
      return statistics.value
    } catch (e) {
      error.value = getApiErrorMessage(e, 'Failed to fetch statistics')
      throw e
    } finally {
      loadingStatistics.value = false
    }
  }

  // ==================== RESET ====================

  function $reset() {
    qualifications.value = []
    currentQualification.value = null
    qualificationsTotal.value = 0
    qualificationsPage.value = 1
    qualificationTypes.value = []
    qualificationTypesLoaded.value = false
    specialTasks.value = []
    currentSpecialTask.value = null
    specialTasksTotal.value = 0
    specialTasksPage.value = 1
    specialTaskTypes.value = []
    specialTaskTypesLoaded.value = false
    statistics.value = null
    qualificationAttachments.value = {}
    specialTaskAttachments.value = {}
    loading.value = false
    loadingDetail.value = false
    loadingStatistics.value = false
    loadingTypes.value = false
    loadingAttachments.value = false
    error.value = null
  }

  // ==================== RETURN ====================

  return {
    // State
    qualifications,
    currentQualification,
    qualificationsTotal,
    qualificationsPage,
    qualificationsPageSize,
    qualificationTypes,
    qualificationTypesLoaded,
    specialTasks,
    currentSpecialTask,
    specialTasksTotal,
    specialTasksPage,
    specialTasksPageSize,
    specialTaskTypes,
    specialTaskTypesLoaded,
    statistics,
    loading,
    loadingDetail,
    loadingStatistics,
    loadingTypes,
    loadingAttachments,
    qualificationAttachments,
    specialTaskAttachments,
    error,

    // Computed
    hasQualifications,
    hasSpecialTasks,
    expiredQualifications,
    expiringQualifications,
    activeQualifications,
    activeSpecialTasks,
    endedSpecialTasks,
    qualificationTypesOptions,
    specialTaskTypesOptions,

    // Actions
    fetchQualifications,
    fetchQualification,
    createQualification,
    updateQualification,
    deleteQualification,
    calculateExpiry,
    fetchQualificationTypes,
    createQualificationType,
    updateQualificationType,
    deleteQualificationType,
    fetchSpecialTasks,
    fetchSpecialTask,
    createSpecialTask,
    updateSpecialTask,
    deleteSpecialTask,
    endSpecialTask,
    fetchQualificationAttachments,
    uploadQualificationAttachment,
    deleteQualificationAttachment,
    fetchSpecialTaskAttachments,
    uploadSpecialTaskAttachment,
    deleteSpecialTaskAttachment,
    fetchSpecialTaskTypes,
    createSpecialTaskType,
    updateSpecialTaskType,
    deleteSpecialTaskType,
    fetchStatistics,
    $reset
  }
})
