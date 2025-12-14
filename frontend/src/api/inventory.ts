/**
 * Inventory API Client
 *
 * Provides methods to interact with the Inventory API endpoints
 */

import apiClient from './index'
import type {
  Category,
  CategoryCreate,
  CategoryUpdate,
  CategoryListParams,
  Item,
  ItemCreate,
  ItemUpdate,
  ItemListParams,
  ItemVariant,
  ItemVariantCreate,
  ItemVariantUpdate,
  ItemVariantListParams,
  StorageLocation,
  StorageLocationCreate,
  StorageLocationUpdate,
  StorageLocationListParams,
  Stock,
  StockListParams,
  StockResponse,
  Transaction,
  TransactionCreate,
  TransactionListParams,
  PaginatedResponse,
  MemberEquipmentResponse
} from '@/types/inventory'

// ==================== Categories ====================

export const categoriesApi = {
  /**
   * List categories with optional filtering
   */
  list(params?: CategoryListParams) {
    return apiClient.get<PaginatedResponse<Category>>('/inventory/categories/', { params })
  },

  /**
   * Get single category by ID
   */
  get(id: number) {
    return apiClient.get<Category>(`/inventory/categories/${id}/`)
  },

  /**
   * Create new category
   */
  create(data: CategoryCreate) {
    return apiClient.post<Category>('/inventory/categories/', data)
  },

  /**
   * Update existing category
   */
  update(id: number, data: CategoryUpdate) {
    return apiClient.patch<Category>(`/inventory/categories/${id}/`, data)
  },

  /**
   * Delete category
   */
  delete(id: number) {
    return apiClient.delete(`/inventory/categories/${id}/`)
  },

  /**
   * Get items in a category
   */
  getItems(id: number) {
    return apiClient.get<PaginatedResponse<Item>>(`/inventory/categories/${id}/items/`)
  }
}

// ==================== Items ====================

export const itemsApi = {
  /**
   * List items with optional filtering
   */
  list(params?: ItemListParams) {
    return apiClient.get<PaginatedResponse<Item>>('/inventory/items/', { params })
  },

  /**
   * Get single item by ID
   */
  get(id: number) {
    return apiClient.get<Item>(`/inventory/items/${id}/`)
  },

  /**
   * Create new item
   */
  create(data: ItemCreate) {
    return apiClient.post<Item>('/inventory/items/', data)
  },

  /**
   * Update existing item
   */
  update(id: number, data: ItemUpdate) {
    return apiClient.patch<Item>(`/inventory/items/${id}/`, data)
  },

  /**
   * Delete item
   */
  delete(id: number) {
    return apiClient.delete(`/inventory/items/${id}/`)
  },

  /**
   * Get item variants
   */
  getVariants(id: number) {
    return apiClient.get<ItemVariant[]>(`/inventory/items/${id}/variants/`)
  },

  /**
   * Get item stock across all locations
   */
  getStock(id: number) {
    return apiClient.get<StockResponse>(`/inventory/items/${id}/stock/`)
  },

  /**
   * Search items
   */
  search(q: string) {
    return apiClient.get<{ results: Item[] }>('/inventory/items/search/', { params: { q } })
  }
}

// ==================== Item Variants ====================

export const variantsApi = {
  /**
   * List item variants with optional filtering
   */
  list(params?: ItemVariantListParams) {
    return apiClient.get<PaginatedResponse<ItemVariant>>('/inventory/variants/', { params })
  },

  /**
   * Get single variant by ID
   */
  get(id: number) {
    return apiClient.get<ItemVariant>(`/inventory/variants/${id}/`)
  },

  /**
   * Create new variant
   */
  create(data: ItemVariantCreate) {
    return apiClient.post<ItemVariant>('/inventory/variants/', data)
  },

  /**
   * Update existing variant
   */
  update(id: number, data: ItemVariantUpdate) {
    return apiClient.patch<ItemVariant>(`/inventory/variants/${id}/`, data)
  },

  /**
   * Delete variant
   */
  delete(id: number) {
    return apiClient.delete(`/inventory/variants/${id}/`)
  },

  /**
   * Get variant stock across all locations
   */
  getStock(id: number) {
    return apiClient.get<StockResponse>(`/inventory/variants/${id}/stock/`)
  }
}

// ==================== Storage Locations ====================

export const locationsApi = {
  /**
   * List storage locations with optional filtering
   */
  list(params?: StorageLocationListParams) {
    return apiClient.get<PaginatedResponse<StorageLocation>>('/inventory/locations/', { params })
  },

  /**
   * Get single location by ID
   */
  get(id: number) {
    return apiClient.get<StorageLocation>(`/inventory/locations/${id}/`)
  },

  /**
   * Create new location
   */
  create(data: StorageLocationCreate) {
    return apiClient.post<StorageLocation>('/inventory/locations/', data)
  },

  /**
   * Update existing location
   */
  update(id: number, data: StorageLocationUpdate) {
    return apiClient.patch<StorageLocation>(`/inventory/locations/${id}/`, data)
  },

  /**
   * Delete location
   */
  delete(id: number) {
    return apiClient.delete(`/inventory/locations/${id}/`)
  },

  /**
   * Get stock at location
   */
  getStock(id: number) {
    return apiClient.get<StockResponse>(`/inventory/locations/${id}/stock/`)
  },

  /**
   * Get or create storage location for a member
   * Auto-creates the location if it doesn't exist
   */
  getForMember(memberId: number) {
    return apiClient.get<StorageLocation>(`/inventory/locations/for-member/${memberId}/`)
  },

  /**
   * Get member's equipment (loaned items) and transaction history
   */
  getMemberEquipment(memberId: number) {
    return apiClient.get<MemberEquipmentResponse>(`/inventory/locations/member-equipment/${memberId}/`)
  }
}

// ==================== Stock ====================

export const stockApi = {
  /**
   * List all stock entries with optional filtering
   */
  list(params?: StockListParams) {
    return apiClient.get<PaginatedResponse<Stock>>('/inventory/stocks/', { params })
  },

  /**
   * Get single stock entry by ID
   */
  get(id: number) {
    return apiClient.get<Stock>(`/inventory/stocks/${id}/`)
  }
}

// ==================== Transactions ====================

export const transactionsApi = {
  /**
   * List transactions with optional filtering
   */
  list(params?: TransactionListParams) {
    return apiClient.get<PaginatedResponse<Transaction>>('/inventory/transactions/', { params })
  },

  /**
   * Get single transaction by ID
   */
  get(id: number) {
    return apiClient.get<Transaction>(`/inventory/transactions/${id}/`)
  },

  /**
   * Create new transaction
   */
  create(data: TransactionCreate) {
    return apiClient.post<Transaction>('/inventory/transactions/', data)
  },

  /**
   * Delete transaction (admin only)
   */
  delete(id: number) {
    return apiClient.delete(`/inventory/transactions/${id}/`)
  }
}

// Combined export for convenience
export const inventoryApi = {
  categories: categoriesApi,
  items: itemsApi,
  variants: variantsApi,
  locations: locationsApi,
  stock: stockApi,
  transactions: transactionsApi
}

export default inventoryApi
