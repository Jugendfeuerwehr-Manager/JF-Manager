/**
 * Orderable Items Store (Catalog)
 * 
 * Manages the catalog of items that can be ordered
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { orderableItemsApi } from '@/api/orderableItems'
import type {
  OrderableItem,
  OrderableItemCreate,
  OrderableItemListParams
} from '@/types/orders'

export const useOrderableItemsStore = defineStore('orderableItems', () => {
  // State
  const items = ref<OrderableItem[]>([])
  const categories = ref<string[]>([])
  const popularItems = ref<OrderableItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const itemsByCategory = computed(() => {
    const grouped: Record<string, OrderableItem[]> = {}
    items.value.forEach(item => {
      if (!grouped[item.category]) {
        grouped[item.category] = []
      }
      grouped[item.category]!.push(item)
    })
    return grouped
  })

  const activeItems = computed(() => 
    items.value.filter(item => item.is_active)
  )

  const itemOptions = computed(() =>
    activeItems.value.map(item => ({
      label: `${item.category} - ${item.name}`,
      value: item.id,
      category: item.category,
      hasSizes: item.has_sizes
    }))
  )

  // Actions
  async function fetchItems(params?: OrderableItemListParams) {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderableItemsApi.list(params)
      items.value = response.data.results
      return items.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch items'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchItem(id: number) {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderableItemsApi.get(id)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch item'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createItem(data: OrderableItemCreate) {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderableItemsApi.create(data)
      items.value.push(response.data)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to create item'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateItem(id: number, data: Partial<OrderableItemCreate>) {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderableItemsApi.update(id, data)
      const index = items.value.findIndex(item => item.id === id)
      if (index !== -1) {
        items.value[index] = response.data
      }
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to update item'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteItem(id: number) {
    loading.value = true
    error.value = null
    
    try {
      await orderableItemsApi.delete(id)
      items.value = items.value.filter(item => item.id !== id)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to delete item'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchCategories() {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderableItemsApi.getCategories()
      categories.value = response.data
      return categories.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch categories'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchItemSizes(id: number) {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderableItemsApi.getSizes(id)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch sizes'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchPopularItems() {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderableItemsApi.getPopular()
      popularItems.value = response.data
      return popularItems.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch popular items'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchItemsByCategory(category: string) {
    loading.value = true
    error.value = null
    
    try {
      const response = await orderableItemsApi.getByCategory(category)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch items by category'
      throw err
    } finally {
      loading.value = false
    }
  }

  function getItemById(id: number) {
    return items.value.find(item => item.id === id)
  }

  function clearError() {
    error.value = null
  }

  function reset() {
    items.value = []
    categories.value = []
    popularItems.value = []
    loading.value = false
    error.value = null
  }

  return {
    // State
    items,
    categories,
    popularItems,
    loading,
    error,
    
    // Computed
    itemsByCategory,
    activeItems,
    itemOptions,
    
    // Actions
    fetchItems,
    fetchItem,
    createItem,
    updateItem,
    deleteItem,
    fetchCategories,
    fetchItemSizes,
    fetchPopularItems,
    fetchItemsByCategory,
    getItemById,
    clearError,
    reset
  }
})
