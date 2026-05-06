import { defineStore } from 'pinia'
import { ref } from 'vue'

import { externalSyncApi } from '@/api/externalSync'
import type {
  GarbageCollectionPreview,
  GarbageCollectionResult,
  SyncJob,
  SyncJobCreate,
  SyncRun,
} from '@/types/externalSync'
import { getApiErrorMessage } from '@/utils/apiError'

export const useExternalSyncStore = defineStore('externalSync', () => {
  const jobs = ref<SyncJob[]>([])
  const runs = ref<SyncRun[]>([])
  const garbageCollectionPreview = ref<GarbageCollectionPreview | null>(null)
  const loading = ref(false)
  const actionJobId = ref<number | null>(null)
  const error = ref<string | null>(null)

  async function fetchJobs(params?: Record<string, unknown>) {
    loading.value = true
    error.value = null
    try {
      const response = await externalSyncApi.listJobs({ limit: 100, ...params })
      jobs.value = response.data.results
      return jobs.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Synchronisationsjobs konnten nicht geladen werden')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchRuns(params?: Record<string, unknown>) {
    loading.value = true
    error.value = null
    try {
      const response = await externalSyncApi.listRuns({ limit: 20, ...params })
      runs.value = response.data.results
      return runs.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Synchronisationsprotokolle konnten nicht geladen werden')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createJob(data: SyncJobCreate) {
    loading.value = true
    error.value = null
    try {
      const response = await externalSyncApi.createJob(data)
      jobs.value.unshift(response.data)
      return response.data
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Synchronisationsjob konnte nicht angelegt werden')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteJob(id: number) {
    actionJobId.value = id
    error.value = null
    try {
      await externalSyncApi.deleteJob(id)
      jobs.value = jobs.value.filter((job) => job.id !== id)
      runs.value = runs.value.filter((run) => run.job !== id)
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Synchronisationsjob konnte nicht gelöscht werden')
      throw err
    } finally {
      actionJobId.value = null
    }
  }

  async function testConnection(id: number) {
    actionJobId.value = id
    error.value = null
    try {
      return await externalSyncApi.testConnection(id)
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Verbindungstest fehlgeschlagen')
      throw err
    } finally {
      await fetchJobs()
      actionJobId.value = null
    }
  }

  async function runNow(id: number) {
    actionJobId.value = id
    error.value = null
    try {
      return await externalSyncApi.runNow(id)
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Synchronisation konnte nicht gestartet werden')
      throw err
    } finally {
      await Promise.all([fetchJobs(), fetchRuns()])
      actionJobId.value = null
    }
  }

  async function fetchGarbageCollectionPreview(id: number) {
    actionJobId.value = id
    error.value = null
    try {
      const response = await externalSyncApi.getGarbageCollectionPreview(id)
      garbageCollectionPreview.value = response.data
      return response.data
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Bereinigungsvorschau konnte nicht geladen werden')
      throw err
    } finally {
      actionJobId.value = null
    }
  }

  async function garbageCollect(id: number) {
    actionJobId.value = id
    error.value = null
    try {
      const response = await externalSyncApi.garbageCollect(id)
      garbageCollectionPreview.value = null
      await Promise.all([fetchJobs(), fetchRuns()])
      return response.data as GarbageCollectionResult
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Bereinigung konnte nicht ausgeführt werden')
      throw err
    } finally {
      actionJobId.value = null
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    jobs,
    runs,
    garbageCollectionPreview,
    loading,
    actionJobId,
    error,
    fetchJobs,
    fetchRuns,
    createJob,
    deleteJob,
    testConnection,
    runNow,
    fetchGarbageCollectionPreview,
    garbageCollect,
    clearError,
  }
})
