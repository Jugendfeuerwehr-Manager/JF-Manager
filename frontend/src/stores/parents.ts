import { defineStore } from 'pinia'
import { ref } from 'vue'
import { parentsApi, type Parent, type MemberParams } from '@/api/members'

export const useParentsStore = defineStore('parents', () => {
  // State
  const parents = ref<Parent[]>([])
  const currentParent = ref<Parent | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({
    count: 0,
    next: null as string | null,
    previous: null as string | null,
    currentPage: 1,
    pageSize: 20
  })

  // Actions
  async function fetchParents(params?: MemberParams) {
    loading.value = true
    error.value = null

    try {
      const response = await parentsApi.getAll(params)
      parents.value = response.data.results
      pagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous,
        currentPage: params?.page || 1,
        pageSize: params?.page_size || 20
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
      const response = await parentsApi.getById(id)
      currentParent.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch parent'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createParent(data: Partial<Parent>) {
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

  async function updateParent(id: number, data: Partial<Parent>) {
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
    // Actions
    fetchParents,
    fetchParentById,
    createParent,
    updateParent,
    deleteParent
  }
})
