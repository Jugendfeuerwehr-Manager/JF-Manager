import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useOrdersStore } from '../orders'
import { ordersApi } from '@/api/orders'
import type { Order, OrderCreate } from '@/types/orders'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'

// Mock API module
vi.mock('@/api/orders')

// Helper to create mock Axios response
function createMockAxiosResponse<T>(data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: { headers: {} } as InternalAxiosRequestConfig
  }
}

describe('Orders Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  const mockOrder: Order = {
    id: 1,
    member: 1,
    member_name: 'Test Member',
    member_group: 'Group A',
    ordered_by: 1,
    ordered_by_name: 'Admin User',
    order_date: '2026-04-12T10:00:00Z',
    notes: 'Test order',
    items: [],
    items_count: 2,
    items_summary: [
      { item_id: 1, item_name: 'Helmet', size: 'M', quantity: 1 },
      { item_id: 2, item_name: 'Gloves', size: 'L', quantity: 1 }
    ],
    common_status: {
      id: 1,
      name: 'Bestellt',
      code: 'ordered',
      color: '#3B82F6'
    },
    status_summary: [
      {
        status_id: 1,
        status_name: 'Bestellt',
        status_code: 'ordered',
        status_color: '#3B82F6',
        count: 2
      }
    ]
  }

  describe('State', () => {
    it('initializes with empty state', () => {
      const store = useOrdersStore()
      
      expect(store.orders).toEqual([])
      expect(store.currentOrder).toBeNull()
      expect(store.statistics).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.pagination.count).toBe(0)
    })
  })

  describe('Computed', () => {
    it('ordersCount returns pagination count', () => {
      const store = useOrdersStore()
      store.pagination.count = 42
      
      expect(store.ordersCount).toBe(42)
    })

    it('hasOrders returns true when orders exist', () => {
      const store = useOrdersStore()
      store.orders = [mockOrder]
      
      expect(store.hasOrders).toBe(true)
    })

    it('hasOrders returns false when no orders', () => {
      const store = useOrdersStore()
      
      expect(store.hasOrders).toBe(false)
    })

    it('ordersByMember groups orders by member', () => {
      const store = useOrdersStore()
      const order1 = { ...mockOrder, id: 1, member: 1 }
      const order2 = { ...mockOrder, id: 2, member: 1 }
      const order3 = { ...mockOrder, id: 3, member: 2 }
      
      store.orders = [order1, order2, order3]
      
      const grouped = store.ordersByMember
      expect(grouped[1]).toHaveLength(2)
      expect(grouped[2]).toHaveLength(1)
    })
  })

  describe('Actions', () => {
    describe('fetchOrders', () => {
      it('fetches orders successfully', async () => {
        const mockResponse = createMockAxiosResponse({
          count: 1,
          next: null,
          previous: null,
          results: [mockOrder]
        })
        
        vi.mocked(ordersApi.list).mockResolvedValue(mockResponse)
        
        const store = useOrdersStore()
        const result = await store.fetchOrders()
        
        expect(result).toEqual([mockOrder])
        expect(store.orders).toEqual([mockOrder])
        expect(store.pagination.count).toBe(1)
        expect(store.loading).toBe(false)
      })

      it('handles fetch error', async () => {
        vi.mocked(ordersApi.list).mockRejectedValue(new Error('Network error'))
        
        const store = useOrdersStore()
        
        await expect(store.fetchOrders()).rejects.toThrow()
        expect(store.error).toBeTruthy()
        expect(store.loading).toBe(false)
      })

      it('passes query parameters to API', async () => {
        const mockResponse = createMockAxiosResponse({
          count: 0,
          next: null,
          previous: null,
          results: []
        })
        
        vi.mocked(ordersApi.list).mockResolvedValue(mockResponse)
        
        const store = useOrdersStore()
        const params = { member: 1, limit: 10 }
        await store.fetchOrders(params)
        
        expect(ordersApi.list).toHaveBeenCalledWith(params)
      })
    })

    describe('fetchOrder', () => {
      it('fetches single order successfully', async () => {
        const mockResponse = createMockAxiosResponse(mockOrder)
        
        vi.mocked(ordersApi.get).mockResolvedValue(mockResponse)
        
        const store = useOrdersStore()
        const result = await store.fetchOrder(1)
        
        expect(result).toEqual(mockOrder)
        expect(store.currentOrder).toEqual(mockOrder)
      })

      it('fetches order with history when requested', async () => {
        const mockResponse = createMockAxiosResponse(mockOrder)
        
        vi.mocked(ordersApi.getWithHistory).mockResolvedValue(mockResponse)
        
        const store = useOrdersStore()
        await store.fetchOrder(1, true)
        
        expect(ordersApi.getWithHistory).toHaveBeenCalledWith(1)
        expect(ordersApi.get).not.toHaveBeenCalled()
      })
    })

    describe('createOrder', () => {
      it('creates order successfully', async () => {
        const newOrderData: OrderCreate = {
          member: 1,
          items: [
            { item: 1, size: 'M', quantity: 1, notes: '' }
          ],
          notes: 'New order'
        }
        
        const mockResponse = createMockAxiosResponse(mockOrder)
        
        vi.mocked(ordersApi.create).mockResolvedValue(mockResponse)
        
        const store = useOrdersStore()
        const result = await store.createOrder(newOrderData)
        
        expect(result).toEqual(mockOrder)
        expect(store.orders[0]).toEqual(mockOrder)
        expect(store.currentOrder).toEqual(mockOrder)
        expect(store.pagination.count).toBe(1)
      })

      it('handles create error', async () => {
        const newOrderData: OrderCreate = {
          member: 1,
          items: [],
          notes: ''
        }
        
        vi.mocked(ordersApi.create).mockRejectedValue(new Error('Validation error'))
        
        const store = useOrdersStore()
        
        await expect(store.createOrder(newOrderData)).rejects.toThrow('Validation error')
        expect(store.error).toBeTruthy()
      })
    })

    describe('clearError', () => {
      it('clears error state', () => {
        const store = useOrdersStore()
        store.error = 'Some error'
        
        store.clearError()
        
        expect(store.error).toBeNull()
      })
    })
  })
})
