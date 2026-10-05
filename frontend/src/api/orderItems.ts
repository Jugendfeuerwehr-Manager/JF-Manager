/**
 * Order Items API Client
 */

import apiClient from './index'
import { withIdempotencyKey } from './idempotency'
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
    // Receiving goods books stock; repeat-safe like other bookings.
    const url = `/order-items/${id}/`
    return withIdempotencyKey('patch', url, data, headers => apiClient.patch<OrderItem>(url, data, { headers }))
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
  updateStatus(id: number, statusId: number, data?: Record<string, unknown>) {
    const url = `/order-items/${id}/update_status/`
    const body = { status: statusId, ...data }
    return withIdempotencyKey('post', url, body, headers => apiClient.post<OrderItem>(url, body, { headers }))
  },

  /**
   * Bulk update status of multiple items
   */
  bulkUpdateStatus(data: BulkStatusUpdateRequest) {
    const url = '/order-items/bulk_update_status/'
    return withIdempotencyKey('post', url, data, headers =>
      apiClient.post<BulkStatusUpdateResponse>(url, data, { headers }),
    )
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
