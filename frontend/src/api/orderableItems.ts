/**
 * Orderable Items API Client (Catalog)
 */

import apiClient from './index'
import type {
  OrderableItem,
  OrderableItemCreate,
  OrderableItemListParams,
  PaginatedResponse
} from '@/types/orders'

export const orderableItemsApi = {
  /**
   * List orderable items
   */
  list(params?: OrderableItemListParams) {
    return apiClient.get<PaginatedResponse<OrderableItem>>('/orderable-items/', { params })
  },

  /**
   * Get single orderable item
   */
  get(id: number) {
    return apiClient.get<OrderableItem>(`/orderable-items/${id}/`)
  },

  /**
   * Create orderable item
   */
  create(data: OrderableItemCreate) {
    return apiClient.post<OrderableItem>('/orderable-items/', data)
  },

  /**
   * Update orderable item
   */
  update(id: number, data: Partial<OrderableItemCreate>) {
    return apiClient.patch<OrderableItem>(`/orderable-items/${id}/`, data)
  },

  /**
   * Delete orderable item
   */
  delete(id: number) {
    return apiClient.delete(`/orderable-items/${id}/`)
  },

  /**
   * Get all categories
   */
  getCategories() {
    return apiClient.get<string[]>('/orderable-items/categories/')
  },

  /**
   * Get sizes for an item
   */
  getSizes(id: number) {
    return apiClient.get<{ has_sizes: boolean; sizes: string[] }>(
      `/orderable-items/${id}/sizes/`
    )
  },

  /**
   * Get popular items
   */
  getPopular() {
    return apiClient.get<OrderableItem[]>('/orderable-items/popular/')
  },

  /**
   * Get items by category
   */
  getByCategory(category: string) {
    return apiClient.get<OrderableItem[]>('/orderable-items/by_category/', {
      params: { category }
    })
  }
}
