/**
 * Order Status Store
 * 
 * Manages order status workflow and transitions
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { orderStatusApi } from '@/api/orderStatus'
import type { OrderStatus } from '@/types/orders'

export const useOrderStatusStore = defineStore('orderStatus', () => {
  // State
  const statuses = ref<OrderStatus[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const activeStatuses = computed(() =>
    statuses.value.filter(status => status.is_active)
  )

  const sortedStatuses = computed(() =>
    [...activeStatuses.value].sort((a, b) => a.sort_order - b.sort_order)
  )

  const statusOptions = computed(() =>
    sortedStatuses.value.map(status => ({
      label: status.name,
      value: status.id,
      code: status.code,
      color: status.color
    }))
  )

  const statusByCode = computed(() => {
    const map: Record<string, OrderStatus> = {}
    statuses.value.forEach(status => {
      map[status.code] = status
    })
    return map
  })

  // Actions
  async function fetchStatuses() {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderStatusApi.list()
      // Extract results from paginated response
      statuses.value = response.data.results
      return statuses.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch statuses'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchActiveStatuses() {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderStatusApi.getActive()
      // Extract results from paginated response
      statuses.value = response.data.results
      return statuses.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch active statuses'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchNextStatuses(statusId: number) {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderStatusApi.getNextStatuses(statusId)
      // Extract results from paginated response
      return response.data.results
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch next statuses'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchWorkflow() {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderStatusApi.getWorkflow()
      // Workflow endpoint returns data directly (not paginated)
      return response.data.results
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch workflow'
      throw err
    } finally {
      loading.value = false
    }
  }

  function getStatusById(id: number) {
    return statuses.value.find(status => status.id === id)
  }

  function getStatusByCode(code: string) {
    return statusByCode.value[code]
  }

  function clearError() {
    error.value = null
  }

  function reset() {
    statuses.value = []
    loading.value = false
    error.value = null
  }

  return {
    // State
    statuses,
    loading,
    error,
    
    // Computed
    activeStatuses,
    sortedStatuses,
    statusOptions,
    statusByCode,
    
    // Actions
    fetchStatuses,
    fetchActiveStatuses,
    fetchNextStatuses,
    fetchWorkflow,
    getStatusById,
    getStatusByCode,
    clearError,
    reset
  }
})
