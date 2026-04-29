import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { trainingSessionsApi } from '@/api/training'
import type {
  TrainingSessionCreate,
  TrainingSessionDetail,
  TrainingSessionHandout,
  TrainingSessionList,
  TrainingSessionUpdate,
} from '@/types/training'

export const useTrainingStore = defineStore('training', () => {
  // ── State ────────────────────────────────────────────────────────────────
  const sessions = ref<TrainingSessionList[]>([])
  const currentSession = ref<TrainingSessionDetail | null>(null)
  const handout = ref<TrainingSessionHandout | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const totalCount = ref(0)

  // ── Getters ──────────────────────────────────────────────────────────────
  const hasSessions = computed(() => sessions.value.length > 0)
  const sessionsByDate = computed(() =>
    [...sessions.value].sort((a, b) => a.date.localeCompare(b.date))
  )

  // ── Actions ──────────────────────────────────────────────────────────────
  async function fetchSessions(params?: Record<string, unknown>) {
    loading.value = true
    error.value = null
    try {
      const response = await trainingSessionsApi.list(params)
      sessions.value = response.data.results
      totalCount.value = response.data.count
      return sessions.value
    } catch (e: unknown) {
      error.value = 'Fehler beim Laden der Trainingseinheiten'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchSession(id: number) {
    loading.value = true
    error.value = null
    try {
      const response = await trainingSessionsApi.get(id)
      currentSession.value = response.data
      return currentSession.value
    } catch (e: unknown) {
      error.value = 'Fehler beim Laden der Trainingseinheit'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchHandout(id: number) {
    loading.value = true
    error.value = null
    try {
      const response = await trainingSessionsApi.handout(id)
      handout.value = response.data
      return handout.value
    } catch (e: unknown) {
      error.value = 'Fehler beim Laden des Handouts'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createSession(data: TrainingSessionCreate) {
    loading.value = true
    error.value = null
    try {
      const response = await trainingSessionsApi.create(data)
      // Add to list
      const listItem: TrainingSessionList = {
        id: response.data.id,
        title: response.data.title,
        date: response.data.date,
        start_time: response.data.start_time,
        end_time: response.data.end_time,
        location: response.data.location,
        group_count: response.data.groups.length,
        groups: response.data.groups,
        block_count: 0,
        series_parent: response.data.series_parent,
        recurrence_rule: response.data.recurrence_rule,
      }
      sessions.value.push(listItem)
      return response.data
    } catch (e: unknown) {
      error.value = 'Fehler beim Erstellen der Trainingseinheit'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateSession(id: number, data: TrainingSessionUpdate) {
    loading.value = true
    error.value = null
    try {
      const response = await trainingSessionsApi.update(id, data)
      const idx = sessions.value.findIndex((s) => s.id === id)
      if (idx !== -1) {
        const existing = sessions.value[idx] as TrainingSessionList
        sessions.value[idx] = {
          ...existing,
          title: response.data.title,
          date: response.data.date,
          start_time: response.data.start_time,
          end_time: response.data.end_time,
          location: response.data.location,
          groups: response.data.groups,
          group_count: response.data.groups.length,
        }
      }
      if (currentSession.value?.id === id) {
        currentSession.value = response.data
      }
      return response.data
    } catch (e: unknown) {
      error.value = 'Fehler beim Aktualisieren der Trainingseinheit'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteSession(id: number) {
    loading.value = true
    error.value = null
    try {
      await trainingSessionsApi.delete(id)
      sessions.value = sessions.value.filter((s) => s.id !== id)
      if (currentSession.value?.id === id) currentSession.value = null
    } catch (e: unknown) {
      error.value = 'Fehler beim Löschen der Trainingseinheit'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function generateSeries(id: number) {
    loading.value = true
    error.value = null
    try {
      const response = await trainingSessionsApi.generateSeries(id)
      return response.data
    } catch (e: unknown) {
      error.value = 'Fehler beim Erstellen der Terminserie'
      throw e
    } finally {
      loading.value = false
    }
  }

  function clearCurrentSession() {
    currentSession.value = null
    handout.value = null
  }

  return {
    sessions,
    currentSession,
    handout,
    loading,
    error,
    totalCount,
    hasSessions,
    sessionsByDate,
    fetchSessions,
    fetchSession,
    fetchHandout,
    createSession,
    updateSession,
    deleteSession,
    generateSeries,
    clearCurrentSession,
  }
})
