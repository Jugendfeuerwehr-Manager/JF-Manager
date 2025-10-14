/**
 * TypeScript types for Orders API
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

export interface OrderStatus {
  id: number
  name: string
  code: string
  description: string
  color: string
  is_active: boolean
  sort_order: number
}

export interface OrderableItem {
  id: number
  name: string
  category: string
  description: string
  has_sizes: boolean
  available_sizes: string
  sizes_list: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface OrderableItemCreate {
  name: string
  category: string
  description?: string
  has_sizes: boolean
  available_sizes?: string
  is_active?: boolean
}

export interface OrderItemStatusHistory {
  id: number
  old_status: number
  old_status_name: string
  new_status: number
  new_status_name: string
  changed_by: number
  changed_by_display: string
  changed_at: string
  notes: string
}

export interface OrderItem {
  id: number
  order: number
  item: number
  item_details: {
    id: number
    name: string
    category: string
    has_sizes: boolean
  }
  item_name: string
  size: string
  quantity: number
  status: number
  status_details: {
    id: number
    name: string
    code: string
    color: string
  }
  status_name: string
  status_color: string
  received_date: string | null
  delivered_date: string | null
  notes: string
}

export interface OrderItemDetailed extends OrderItem {
  status_history?: OrderItemStatusHistory[]
}

export interface OrderItemCreate {
  item: number
  size?: string
  quantity: number
  status?: number
  notes?: string
}

export interface OrderItemUpdate {
  size?: string
  quantity?: number
  status?: number
  notes?: string
}

export interface Order {
  id: number
  member: number
  member_name: string
  member_group: string
  ordered_by: number
  ordered_by_name: string
  order_date: string
  notes: string
  items: OrderItem[]
  items_count: number
  items_summary: {
    item_id: number
    item_name: string
    size: string
    quantity: number
  }[]
  common_status: {
    id: number
    name: string
    code: string
    color: string
  } | null
  status_summary: {
    status_id: number
    status_name: string
    status_code: string
    status_color: string
    count: number
  }[]
}

export interface OrderDetailed extends Order {
  items: OrderItemDetailed[]
}

export interface OrderCreate {
  member: number
  notes?: string
  items: OrderItemCreate[]
}

export interface OrderUpdate {
  member?: number
  notes?: string
}

export interface QuickOrderItem {
  item_id: number
  size?: string
  quantity?: number
}

export interface QuickOrderCreate {
  member: number
  items: QuickOrderItem[]
  notes?: string
}

// List/Filter parameters
export interface OrderListParams {
  limit?: number
  offset?: number
  member?: number
  member_name?: string
  ordered_by?: number
  date_from?: string
  date_to?: string
  status?: number
  has_status?: string
  search?: string
  ordering?: string
}

export interface OrderItemListParams {
  limit?: number
  offset?: number
  order?: number
  member?: number
  status?: number
  status_code?: string
  item?: number
  item_category?: string
  date_from?: string
  date_to?: string
  has_size?: boolean
  search?: string
  ordering?: string
}

export interface OrderableItemListParams {
  limit?: number
  offset?: number
  category?: string
  has_sizes?: boolean
  is_active?: boolean
  search?: string
  ordering?: string
}

// Statistics
export interface OrderStatistics {
  total_orders: number
  total_items: number
  status_breakdown: {
    status__name: string
    status__code: string
    status__color: string
    count: number
  }[]
  category_breakdown: {
    item__category: string
    count: number
  }[]
  top_members: {
    member__id: number
    member__name: string
    member__lastname: string
    order_count: number
  }[]
  monthly_trend: {
    month: string
    count: number
  }[]
  pending_items: number
  delivered_items: number
}

export interface OrderItemStatistics {
  total: number
  by_status: {
    status__name: string
    status__code: string
    status__color: string
    count: number
  }[]
  by_category: {
    item__category: string
    count: number
  }[]
  pending: number
  delivered: number
}

// Bulk operations
export interface BulkStatusUpdateRequest {
  item_ids: number[]
  status: number
  notes?: string
}

export interface BulkStatusUpdateResponse {
  updated: number
  updated_ids: number[]
  errors: {
    item_id: number
    errors: any
  }[]
}

// Pagination
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
