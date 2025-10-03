import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { parentsApi, type Parent, type ParentCreate, type MemberListParams } from '@/api/members'

export const useParentsStore = defineStore('parents', () => {
  // State
  const parents = ref<Parent[]>([])
  const currentParent = ref<Parent | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({
    count: 0,
    next: null as string | null,
    previous: null as string | null
  })

  // Computed
  const parentOptions = computed(() => 
    parents.value.map(p => ({ 
      label: p.full_name, 
      value: p.id 
    }))
  )

  // Actions
  async function fetchParents(params?: MemberListParams) {
    loading.value = true
    error.value = null

    try {
      const response = await parentsApi.list(params)
      parents.value = response.data.results
      pagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch parents'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchParentById(id: number) {
    loading.value = true
    error.value = null

    try {
      const response = await parentsApi.get(id)
      currentParent.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch parent'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createParent(data: ParentCreate) {
    loading.value = true
    error.value = null

    try {
      const response = await parentsApi.create(data)
      parents.value.unshift(response.data)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to create parent'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateParent(id: number, data: Partial<ParentCreate>) {
    loading.value = true
    error.value = null

    try {
      const response = await parentsApi.update(id, data)
      const index = parents.value.findIndex((p) => p.id === id)
      if (index !== -1) {
        parents.value[index] = response.data
      }
      if (currentParent.value?.id === id) {
        currentParent.value = response.data
      }
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to update parent'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteParent(id: number) {
    loading.value = true
    error.value = null

    try {
      await parentsApi.delete(id)
      parents.value = parents.value.filter((p) => p.id !== id)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to delete parent'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    parents,
    currentParent,
    loading,
    error,
    pagination,
    // Computed
    parentOptions,
    // Actions
    fetchParents,
    fetchParentById,
    createParent,
    updateParent,
    deleteParent,
    resetStore: () => {
      parents.value = []
      currentParent.value = null
      error.value = null
      pagination.value = {
        count: 0,
        next: null,
        previous: null
      }
    }
  }
})
