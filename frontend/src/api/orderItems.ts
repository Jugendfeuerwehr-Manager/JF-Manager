/**
 * Order Items API Client
 */

import apiClient from './index'
import type {
  OrderItem,
  OrderItemCreate,
  OrderItemUpdate,
  OrderItemListParams,
  OrderItemStatistics,
  OrderItemStatusHistory,
  BulkStatusUpdateRequest,
  BulkStatusUpdateResponse,
  PaginatedResponse
} from '@/types/orders'

export const orderItemsApi = {
  /**
   * List order items with filtering
   */
  list(params?: OrderItemListParams) {
    return apiClient.get<PaginatedResponse<OrderItem>>('/order-items/', { params })
  },

  /**
   * Get single order item
   */
  get(id: number) {
    return apiClient.get<OrderItem>(`/order-items/${id}/`)
  },

  /**
   * Create order item
   */
  create(data: OrderItemCreate) {
    return apiClient.post<OrderItem>('/order-items/', data)
  },

  /**
   * Update order item
   */
  update(id: number, data: OrderItemUpdate) {
    return apiClient.patch<OrderItem>(`/order-items/${id}/`, data)
  },

  /**
   * Delete order item
   */
  delete(id: number) {
    return apiClient.delete(`/order-items/${id}/`)
  },

  /**
   * Update status of single order item
   */
  updateStatus(id: number, statusId: number, data?: any) {
    return apiClient.post<OrderItem>(`/order-items/${id}/update_status/`, {
      status: statusId,
      ...data
    })
  },

  /**
   * Bulk update status of multiple items
   */
  bulkUpdateStatus(data: BulkStatusUpdateRequest) {
    return apiClient.post<BulkStatusUpdateResponse>('/order-items/bulk_update_status/', data)
  },

  /**
   * Get status history for order item
   */
  getHistory(id: number) {
    return apiClient.get<OrderItemStatusHistory[]>(`/order-items/${id}/history/`)
  },

  /**
   * Get order item statistics
   */
  getStatistics(params?: OrderItemListParams) {
    return apiClient.get<OrderItemStatistics>('/order-items/statistics/', { params })
  }
}
