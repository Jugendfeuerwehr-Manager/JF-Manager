/**
 * TypeScript types for Inventory API
 *
 * These types match the backend serializers exactly
 */

/**
 * Django REST Framework paginated response
 */
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/**
 * Category for inventory items
 */
export interface Category {
  id: number
  name: string
  schema: Record<string, string> | null
  item_count?: number
}

export interface CategoryCreate {
  name: string
  schema?: Record<string, string> | null
}

export interface CategoryUpdate {
  name?: string
  schema?: Record<string, string> | null
}

/**
 * Item variant (e.g., Hose Gr. 164, Hose Gr. 176)
 */
export interface ItemVariant {
  id: number
  parent_item: number
  parent_item_name: string
  category_id: number | null
  category_name: string | null
  sku: string
  variant_attributes: Record<string, string>
  total_stock: number
}

export interface ItemVariantCreate {
  parent_item: number
  sku?: string
  variant_attributes: Record<string, string>
}

export interface ItemVariantUpdate {
  sku?: string
  variant_attributes?: Record<string, string>
}

/**
 * Inventory item (main article without variant-specific data)
 */
export interface Item {
  id: number
  name: string
  category: number | null
  category_name: string | null
  base_unit: string
  attributes: Record<string, unknown> | null
  is_variant_parent: boolean
  // Legacy fields
  size: string
  identifier1: string
  identifier2: string
  rented_by: number | null
  total_stock: number
  variants: ItemVariant[]
}

export interface ItemCreate {
  name: string
  category: number
  base_unit?: string
  attributes?: Record<string, unknown> | null
  is_variant_parent?: boolean
  size?: string
  identifier1?: string
  identifier2?: string
}

export interface ItemUpdate {
  name?: string
  category?: number
  base_unit?: string
  attributes?: Record<string, unknown> | null
  is_variant_parent?: boolean
  size?: string
  identifier1?: string
  identifier2?: string
  rented_by?: number | null
}

/**
 * Storage location with hierarchical structure
 */
export interface StorageLocation {
  id: number
  name: string
  parent: number | null
  parent_name: string | null
  is_member: boolean
  member: number | null
  full_path: string
}

export interface StorageLocationCreate {
  name: string
  parent?: number | null
  is_member?: boolean
  member?: number | null
}

export interface StorageLocationUpdate {
  name?: string
  parent?: number | null
  is_member?: boolean
  member?: number | null
}

/**
 * Stock of an item/variant at a location
 */
export interface Stock {
  id: number
  item: number | null
  item_name: string | null
  item_variant: number | null
  variant_display: string | null
  location: number
  location_name: string
  quantity: number
  category_id: number | null
  category_name: string | null
  display_name: string
}

/**
 * Transaction types
 */
export type TransactionType = 'IN' | 'OUT' | 'MOVE' | 'LOAN' | 'RETURN' | 'DISCARD'

export const TRANSACTION_TYPES: { value: TransactionType; label: string; icon: string; color: string }[] = [
  { value: 'IN', label: 'Eingang', icon: 'pi-arrow-down', color: 'success' },
  { value: 'OUT', label: 'Ausgang', icon: 'pi-arrow-up', color: 'warning' },
  { value: 'MOVE', label: 'Umlagerung', icon: 'pi-arrows-h', color: 'info' },
  { value: 'LOAN', label: 'Ausleihe', icon: 'pi-user', color: 'primary' },
  { value: 'RETURN', label: 'Rückgabe', icon: 'pi-replay', color: 'secondary' },
  { value: 'DISCARD', label: 'Aussortierung', icon: 'pi-trash', color: 'danger' }
]

/**
 * Transaction for stock changes
 */
export interface Transaction {
  id: number
  transaction_type: TransactionType
  item: number | null
  item_variant: number | null
  item_name: string
  source: number | null
  source_name: string | null
  target: number | null
  target_name: string | null
  quantity: number
  date: string
  note: string
  user: number | null
  user_username: string | null
}

export interface TransactionCreate {
  transaction_type: TransactionType
  item?: number | null
  item_variant?: number | null
  source?: number | null
  target?: number | null
  quantity: number
  note?: string
}

/**
 * API list parameters
 */
export interface CategoryListParams {
  search?: string
  name?: string
  limit?: number
  offset?: number
}

export interface ItemListParams {
  search?: string
  category?: number
  is_variant_parent?: boolean
  limit?: number
  offset?: number
}

export interface ItemVariantListParams {
  search?: string
  parent_item?: number
  parent_item__category?: number
  limit?: number
  offset?: number
}

export interface StorageLocationListParams {
  search?: string
  parent?: number
  is_member?: boolean
  member?: number
  limit?: number
  offset?: number
}

export interface StockListParams {
  search?: string
  item?: number
  item_variant?: number
  location?: number
  limit?: number
  offset?: number
}

export interface TransactionListParams {
  search?: string
  transaction_type?: TransactionType
  item?: number
  item_variant?: number
  source?: number
  target?: number
  limit?: number
  offset?: number
}

/**
 * Stock response from item/variant/location stock endpoint
 */
export interface StockResponse {
  total: number
  rows: Stock[]
}

/**
 * Member equipment response - items loaned to a specific member
 */
export interface MemberEquipmentResponse {
  member_id: number
  member_name: string
  location_id: number | null
  equipment: Stock[]
  total_items: number
  recent_transactions: Transaction[]
}

/**
 * Member loan summary - items loaned to a specific member
 */
export interface MemberLoan {
  member_id: number
  member_name: string
  location_id: number
  items: {
    stock_id: number
    item_id: number | null
    item_name: string | null
    variant_id: number | null
    variant_display: string | null
    quantity: number
    category_name: string | null
  }[]
  total_items: number
}

/**
 * Dashboard statistics
 */
export interface InventoryStatistics {
  total_items: number
  total_variants: number
  total_categories: number
  total_locations: number
  total_stock: number
  items_on_loan: number
  recent_transactions: Transaction[]
}
