/**
 * Pinia store for member groups
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '@/api'

export interface Group {
  id: number
  name: string
}

export const useGroupsStore = defineStore('groups', () => {
  // State
  const groups = ref<Group[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  async function fetchGroups(params?: any) {
    loading.value = true
    error.value = null

    try {
      const response = await apiClient.get<{ results: Group[] }>('/groups/', { params })
      groups.value = response.data.results
      return groups.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Fehler beim Laden der Gruppen'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    groups,
    loading,
    error,
    fetchGroups
  }
})
