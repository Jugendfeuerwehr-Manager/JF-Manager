/**
 * Orders Pinia Store
 * 
 * Manages orders state and operations
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ordersApi } from '@/api/orders'
import type {
  Order,
  OrderCreate,
  OrderUpdate,
  OrderListParams,
  OrderStatistics,
  QuickOrderCreate
} from '@/types/orders'

export const useOrdersStore = defineStore('orders', () => {
  // State
  const orders = ref<Order[]>([])
  const currentOrder = ref<Order | null>(null)
  const statistics = ref<OrderStatistics | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({
    count: 0,
    next: null as string | null,
    previous: null as string | null
  })

  // Computed
  const ordersCount = computed(() => pagination.value.count)
  const hasOrders = computed(() => orders.value.length > 0)
  const isLoading = computed(() => loading.value)
  
  const ordersByMember = computed(() => {
    const grouped: Record<number, Order[]> = {}
    orders.value.forEach(order => {
      if (!grouped[order.member]) {
        grouped[order.member] = []
      }
      grouped[order.member]!.push(order)
    })
    return grouped
  })

  // Actions
  async function fetchOrders(params?: OrderListParams) {
    loading.value = true
    error.value = null
    
    try {
      const response = await ordersApi.list(params)
      orders.value = response.data.results
      pagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous
      }
      return orders.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch orders'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchOrder(id: number, withHistory: boolean = false) {
    loading.value = true
    error.value = null
    
    try {
      const response = withHistory 
        ? await ordersApi.getWithHistory(id)
        : await ordersApi.get(id)
      
      currentOrder.value = response.data
      return currentOrder.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch order'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createOrder(data: OrderCreate) {
    loading.value = true
    error.value = null
    
    try {
      const response = await ordersApi.create(data)
      orders.value.unshift(response.data)
      currentOrder.value = response.data
      pagination.value.count++
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to create order'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function quickCreateOrder(data: QuickOrderCreate) {
    loading.value = true
    error.value = null
    
    try {
      const response = await ordersApi.quickCreate(data)
      orders.value.unshift(response.data)
      currentOrder.value = response.data
      pagination.value.count++
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to create quick order'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateOrder(id: number, data: OrderUpdate) {
    loading.value = true
    error.value = null
    
    try {
      const response = await ordersApi.update(id, data)
      
      // Update in list
      const index = orders.value.findIndex(o => o.id === id)
      if (index !== -1) {
        orders.value[index] = response.data
      }
      
      // Update current order if it's the one being updated
      if (currentOrder.value?.id === id) {
        currentOrder.value = response.data
      }
      
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to update order'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteOrder(id: number) {
    loading.value = true
    error.value = null
    
    try {
      await ordersApi.delete(id)
      
      // Remove from list
      orders.value = orders.value.filter(o => o.id !== id)
      
      // Clear current order if it's the one being deleted
      if (currentOrder.value?.id === id) {
        currentOrder.value = null
      }
      
      pagination.value.count--
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to delete order'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchStatistics(params?: OrderListParams) {
    loading.value = true
    error.value = null
    
    try {
      const response = await ordersApi.getStatistics(params)
      statistics.value = response.data
      return statistics.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch statistics'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchRecentOrders(limit: number = 10) {
    loading.value = true
    error.value = null
    
    try {
      const response = await ordersApi.getRecent(limit)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch recent orders'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchPendingOrders() {
    loading.value = true
    error.value = null
    
    try {
      const response = await ordersApi.getPending()
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch pending orders'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchOrdersByMember(memberId: number) {
    loading.value = true
    error.value = null
    
    try {
      const response = await ordersApi.getByMember(memberId)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch member orders'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function exportOrders(params?: OrderListParams) {
    loading.value = true
    error.value = null
    
    try {
      const response = await ordersApi.export(params)
      
      // Create download link
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `orders_${new Date().toISOString().split('T')[0]}.csv`
      link.click()
      window.URL.revokeObjectURL(url)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to export orders'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function sendSummary(data: {
    recipient_email: string
    include_notes?: boolean
    group_by_category?: boolean
    additional_notes?: string
  }) {
    loading.value = true
    error.value = null
    
    try {
      const response = await ordersApi.sendSummary(data)
      // Note: The backend updates order statuses from NEW to ORDERED
      // The calling component should refresh the orders list to reflect changes
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to send order summary'
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  function clearCurrentOrder() {
    currentOrder.value = null
  }

  function reset() {
    orders.value = []
    currentOrder.value = null
    statistics.value = null
    loading.value = false
    error.value = null
    pagination.value = {
      count: 0,
      next: null,
      previous: null
    }
  }

  return {
    // State
    orders,
    currentOrder,
    statistics,
    loading,
    error,
    pagination,
    
    // Computed
    ordersCount,
    hasOrders,
    isLoading,
    ordersByMember,
    
    // Actions
    fetchOrders,
    fetchOrder,
    createOrder,
    quickCreateOrder,
    updateOrder,
    deleteOrder,
    fetchStatistics,
    fetchRecentOrders,
    fetchPendingOrders,
    fetchOrdersByMember,
    exportOrders,
    sendSummary,
    clearError,
    clearCurrentOrder,
    reset
  }
})
