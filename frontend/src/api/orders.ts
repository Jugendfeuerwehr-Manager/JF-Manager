/**
 * Orders API Client
 * 
 * Provides methods to interact with the Orders API endpoints
 */

import apiClient from './index'
import type {
  Order,
  OrderCreate,
  OrderUpdate,
  OrderListParams,
  OrderStatistics,
  QuickOrderCreate,
  PaginatedResponse
} from '@/types/orders'

export const ordersApi = {
  /**
   * List orders with optional filtering
   */
  list(params?: OrderListParams) {
    return apiClient.get<PaginatedResponse<Order>>('/orders/', { params })
  },

  /**
   * Get single order by ID
   */
  get(id: number) {
    return apiClient.get<Order>(`/orders/${id}/`)
  },

  /**
   * Get order with full history
   */
  getWithHistory(id: number) {
    return apiClient.get<Order>(`/orders/${id}/detail_with_history/`)
  },

  /**
   * Create new order
   */
  create(data: OrderCreate) {
    return apiClient.post<Order>('/orders/', data)
  },

  /**
   * Update existing order
   */
  update(id: number, data: OrderUpdate) {
    return apiClient.patch<Order>(`/orders/${id}/`, data)
  },

  /**
   * Delete order
   */
  delete(id: number) {
    return apiClient.delete(`/orders/${id}/`)
  },

  /**
   * Quick order creation
   */
  quickCreate(data: QuickOrderCreate) {
    return apiClient.post<Order>('/orders/quick_create/', data)
  },

  /**
   * Get order statistics
   */
  getStatistics(params?: OrderListParams) {
    return apiClient.get<OrderStatistics>('/orders/statistics/', { params })
  },

  /**
   * Get recent orders
   */
  getRecent(limit: number = 10) {
    return apiClient.get<Order[]>('/orders/recent/', { params: { limit } })
  },

  /**
   * Get pending orders
   */
  getPending() {
    return apiClient.get<Order[]>('/orders/pending/')
  },

  /**
   * Get orders for specific member
   */
  getByMember(memberId: number) {
    return apiClient.get<Order[]>('/orders/by_member/', {
      params: { member_id: memberId }
    })
  },

  /**
   * Export orders to CSV
   */
  export(params?: OrderListParams) {
    return apiClient.get('/orders/export/', {
      params,
      responseType: 'blob'
    })
  },

  /**
   * Send order summary to Gerätewart
   */
  sendSummary(data: {
    recipient_email: string
    status_filter?: number[]
    date_from?: string
    date_to?: string
    include_notes?: boolean
    group_by_category?: boolean
    additional_notes?: string
  }) {
    return apiClient.post('/orders/send_summary/', data)
  }
}
