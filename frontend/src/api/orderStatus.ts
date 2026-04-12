/**
 * Order Status API Client
 */

import apiClient from './index'
import type { OrderStatus, PaginatedResponse } from '@/types/orders'

export const orderStatusApi = {
  /**
   * List all order statuses
   */
  list() {
    return apiClient.get<PaginatedResponse<OrderStatus>>('/order-statuses/')
  },

  /**
   * Get single order status
   */
  get(id: number) {
    return apiClient.get<OrderStatus>(`/order-statuses/${id}/`)
  },

  /**
   * Get only active statuses
   */
  getActive() {
    return apiClient.get<PaginatedResponse<OrderStatus>>('/order-statuses/?is_active=true')
  },

  /**
   * Get next allowed statuses from current status
   */
  getNextStatuses(statusId: number) {
    return apiClient.get<PaginatedResponse<OrderStatus>>(`/order-statuses/${statusId}/next_statuses/`)
  },

  /**
   * Get complete workflow information
   */
  getWorkflow() {
    return apiClient.get<Record<string, unknown>>('/order-statuses/workflow/')
  },

  /**
   * Create new status (admin only)
   */
  create(data: Omit<OrderStatus, 'id'>) {
    return apiClient.post<OrderStatus>('/order-statuses/', data)
  },

  /**
   * Update status (admin only)
   */
  update(id: number, data: Partial<Omit<OrderStatus, 'id'>>) {
    return apiClient.patch<OrderStatus>(`/order-statuses/${id}/`, data)
  },

  /**
   * Delete status (admin only)
   */
  delete(id: number) {
    return apiClient.delete(`/order-statuses/${id}/`)
  }
}
