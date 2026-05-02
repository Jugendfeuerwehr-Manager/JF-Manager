/**
 * Inventory Pinia Store
 *
 * Manages inventory state and operations
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  categoriesApi,
  itemsApi,
  variantsApi,
  locationsApi,
  stockApi,
  transactionsApi
} from '@/api/inventory'
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
  Transaction,
  TransactionCreate,
  TransactionListParams,
  MemberLoan
} from '@/types/inventory'

export const useInventoryStore = defineStore('inventory', () => {
  // ==================== State ====================

  // Categories
  const categories = ref<Category[]>([])
  const categoriesLoading = ref(false)
  const categoriesPagination = ref({ count: 0, next: null as string | null, previous: null as string | null })

  // Items
  const items = ref<Item[]>([])
  const currentItem = ref<Item | null>(null)
  const itemsLoading = ref(false)
  const itemsPagination = ref({ count: 0, next: null as string | null, previous: null as string | null })

  // Variants
  const variants = ref<ItemVariant[]>([])
  const variantsLoading = ref(false)
  const variantsPagination = ref({ count: 0, next: null as string | null, previous: null as string | null })

  // Locations
  const locations = ref<StorageLocation[]>([])
  const currentLocation = ref<StorageLocation | null>(null)
  const locationsLoading = ref(false)
  const locationsPagination = ref({ count: 0, next: null as string | null, previous: null as string | null })

  // Stock
  const stocks = ref<Stock[]>([])
  const stocksLoading = ref(false)
  const stocksPagination = ref({ count: 0, next: null as string | null, previous: null as string | null })

  // Transactions
  const transactions = ref<Transaction[]>([])
  const transactionsLoading = ref(false)
  const transactionsPagination = ref({ count: 0, next: null as string | null, previous: null as string | null })

  // General
  const error = ref<string | null>(null)

  // ==================== Computed ====================

  const categoryOptions = computed(() =>
    categories.value.map((c) => ({
      label: `${c.name} [G]`,
      value: c.id
    }))
  )

  const locationOptions = computed(() =>
    locations.value.map((l) => ({
      label: `${l.full_path || l.name}${l.department === null ? ' [G]' : ''}`,
      value: l.id,
      is_member: l.is_member
    }))
  )

  const memberLocations = computed(() =>
    locations.value.filter((l) => l.is_member)
  )

  const storageLocations = computed(() =>
    locations.value.filter((l) => !l.is_member)
  )

  const itemOptions = computed(() =>
    items.value.map((i) => ({
      label: `${i.name}${i.department === null ? ' [G]' : ''}`,
      value: i.id,
      category: i.category_name,
      has_variants: i.is_variant_parent
    }))
  )

  /**
   * Get member loans - items loaned to members
   */
  const memberLoans = computed<MemberLoan[]>(() => {
    const loansMap = new Map<number, MemberLoan>()

    // Filter stocks at member locations
    stocks.value
      .filter((stock) => {
        const location = locations.value.find((l) => l.id === stock.location)
        return location?.is_member && stock.quantity > 0
      })
      .forEach((stock) => {
        const location = locations.value.find((l) => l.id === stock.location)
        if (!location?.member) return

        const memberId = location.member
        if (!loansMap.has(memberId)) {
          loansMap.set(memberId, {
            member_id: memberId,
            member_name: location.name,
            location_id: location.id,
            items: [],
            total_items: 0
          })
        }

        const loan = loansMap.get(memberId)!
        loan.items.push({
          stock_id: stock.id,
          item_id: stock.item,
          item_name: stock.item_name,
          variant_id: stock.item_variant,
          variant_display: stock.variant_display,
          quantity: stock.quantity,
          category_name: categories.value.find((c) => c.id === stock.category_id)?.name || null
        })
        loan.total_items += stock.quantity
      })

    return Array.from(loansMap.values()).sort((a, b) => a.member_name.localeCompare(b.member_name))
  })

  // ==================== Actions - Categories ====================

  async function fetchCategories(params?: CategoryListParams) {
    categoriesLoading.value = true
    error.value = null
    try {
      const response = await categoriesApi.list(params)
      categories.value = response.data.results
      categoriesPagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous
      }
      return categories.value
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to fetch categories'
      throw err
    } finally {
      categoriesLoading.value = false
    }
  }

  async function createCategory(data: CategoryCreate) {
    categoriesLoading.value = true
    error.value = null
    try {
      const response = await categoriesApi.create(data)
      categories.value.push(response.data)
      return response.data
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create category'
      throw err
    } finally {
      categoriesLoading.value = false
    }
  }

  async function updateCategory(id: number, data: CategoryUpdate) {
    categoriesLoading.value = true
    error.value = null
    try {
      const response = await categoriesApi.update(id, data)
      const index = categories.value.findIndex((c) => c.id === id)
      if (index !== -1) {
        categories.value[index] = response.data
      }
      return response.data
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to update category'
      throw err
    } finally {
      categoriesLoading.value = false
    }
  }

  async function deleteCategory(id: number) {
    categoriesLoading.value = true
    error.value = null
    try {
      await categoriesApi.delete(id)
      categories.value = categories.value.filter((c) => c.id !== id)
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to delete category'
      throw err
    } finally {
      categoriesLoading.value = false
    }
  }

  // ==================== Actions - Items ====================

  async function fetchItems(params?: ItemListParams) {
    itemsLoading.value = true
    error.value = null
    try {
      const response = await itemsApi.list(params)
      items.value = response.data.results
      itemsPagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous
      }
      return items.value
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to fetch items'
      throw err
    } finally {
      itemsLoading.value = false
    }
  }

  async function fetchItem(id: number) {
    itemsLoading.value = true
    error.value = null
    try {
      const response = await itemsApi.get(id)
      currentItem.value = response.data
      return currentItem.value
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to fetch item'
      throw err
    } finally {
      itemsLoading.value = false
    }
  }

  async function createItem(data: ItemCreate) {
    itemsLoading.value = true
    error.value = null
    try {
      const response = await itemsApi.create(data)
      items.value.unshift(response.data)
      itemsPagination.value.count++
      return response.data
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create item'
      throw err
    } finally {
      itemsLoading.value = false
    }
  }

  async function updateItem(id: number, data: ItemUpdate) {
    itemsLoading.value = true
    error.value = null
    try {
      const response = await itemsApi.update(id, data)
      const index = items.value.findIndex((i) => i.id === id)
      if (index !== -1) {
        items.value[index] = response.data
      }
      if (currentItem.value?.id === id) {
        currentItem.value = response.data
      }
      return response.data
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to update item'
      throw err
    } finally {
      itemsLoading.value = false
    }
  }

  async function deleteItem(id: number) {
    itemsLoading.value = true
    error.value = null
    try {
      await itemsApi.delete(id)
      items.value = items.value.filter((i) => i.id !== id)
      if (currentItem.value?.id === id) {
        currentItem.value = null
      }
      itemsPagination.value.count--
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to delete item'
      throw err
    } finally {
      itemsLoading.value = false
    }
  }

  async function searchItems(query: string) {
    itemsLoading.value = true
    error.value = null
    try {
      const response = await itemsApi.search(query)
      return response.data.results
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to search items'
      throw err
    } finally {
      itemsLoading.value = false
    }
  }

  // ==================== Actions - Variants ====================

  async function fetchVariants(params?: ItemVariantListParams) {
    variantsLoading.value = true
    error.value = null
    try {
      const response = await variantsApi.list(params)
      variants.value = response.data.results
      variantsPagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous
      }
      return variants.value
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to fetch variants'
      throw err
    } finally {
      variantsLoading.value = false
    }
  }

  async function createVariant(data: ItemVariantCreate) {
    variantsLoading.value = true
    error.value = null
    try {
      const response = await variantsApi.create(data)
      variants.value.push(response.data)
      return response.data
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create variant'
      throw err
    } finally {
      variantsLoading.value = false
    }
  }

  async function updateVariant(id: number, data: ItemVariantUpdate) {
    variantsLoading.value = true
    error.value = null
    try {
      const response = await variantsApi.update(id, data)
      const index = variants.value.findIndex((v) => v.id === id)
      if (index !== -1) {
        variants.value[index] = response.data
      }
      return response.data
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to update variant'
      throw err
    } finally {
      variantsLoading.value = false
    }
  }

  async function deleteVariant(id: number) {
    variantsLoading.value = true
    error.value = null
    try {
      await variantsApi.delete(id)
      variants.value = variants.value.filter((v) => v.id !== id)
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to delete variant'
      throw err
    } finally {
      variantsLoading.value = false
    }
  }

  // ==================== Actions - Locations ====================

  async function fetchLocations(params?: StorageLocationListParams) {
    locationsLoading.value = true
    error.value = null
    try {
      const response = await locationsApi.list(params)
      locations.value = response.data.results
      locationsPagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous
      }
      return locations.value
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to fetch locations'
      throw err
    } finally {
      locationsLoading.value = false
    }
  }

  async function fetchLocation(id: number) {
    locationsLoading.value = true
    error.value = null
    try {
      const response = await locationsApi.get(id)
      currentLocation.value = response.data
      return currentLocation.value
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to fetch location'
      throw err
    } finally {
      locationsLoading.value = false
    }
  }

  async function createLocation(data: StorageLocationCreate) {
    locationsLoading.value = true
    error.value = null
    try {
      const response = await locationsApi.create(data)
      locations.value.push(response.data)
      locationsPagination.value.count++
      return response.data
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create location'
      throw err
    } finally {
      locationsLoading.value = false
    }
  }

  async function updateLocation(id: number, data: StorageLocationUpdate) {
    locationsLoading.value = true
    error.value = null
    try {
      const response = await locationsApi.update(id, data)
      const index = locations.value.findIndex((l) => l.id === id)
      if (index !== -1) {
        locations.value[index] = response.data
      }
      if (currentLocation.value?.id === id) {
        currentLocation.value = response.data
      }
      return response.data
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to update location'
      throw err
    } finally {
      locationsLoading.value = false
    }
  }

  async function deleteLocation(id: number) {
    locationsLoading.value = true
    error.value = null
    try {
      await locationsApi.delete(id)
      locations.value = locations.value.filter((l) => l.id !== id)
      if (currentLocation.value?.id === id) {
        currentLocation.value = null
      }
      locationsPagination.value.count--
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to delete location'
      throw err
    } finally {
      locationsLoading.value = false
    }
  }

  async function fetchLocationStock(id: number) {
    stocksLoading.value = true
    error.value = null
    try {
      const response = await locationsApi.getStock(id)
      return response.data
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to fetch location stock'
      throw err
    } finally {
      stocksLoading.value = false
    }
  }

  // ==================== Actions - Stock ====================

  async function fetchStocks(params?: StockListParams) {
    stocksLoading.value = true
    error.value = null
    try {
      const response = await stockApi.list(params)
      stocks.value = response.data.results
      stocksPagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous
      }
      return stocks.value
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to fetch stocks'
      throw err
    } finally {
      stocksLoading.value = false
    }
  }

  // ==================== Actions - Transactions ====================

  async function fetchTransactions(params?: TransactionListParams) {
    transactionsLoading.value = true
    error.value = null
    try {
      const response = await transactionsApi.list(params)
      transactions.value = response.data.results
      transactionsPagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous
      }
      return transactions.value
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to fetch transactions'
      throw err
    } finally {
      transactionsLoading.value = false
    }
  }

  async function createTransaction(data: TransactionCreate) {
    transactionsLoading.value = true
    error.value = null
    try {
      const response = await transactionsApi.create(data)
      transactions.value.unshift(response.data)
      transactionsPagination.value.count++

      // Refresh stock after transaction
      await fetchStocks({ limit: 1000 })

      return response.data
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create transaction'
      throw err
    } finally {
      transactionsLoading.value = false
    }
  }

  async function deleteTransaction(id: number) {
    transactionsLoading.value = true
    error.value = null
    try {
      await transactionsApi.delete(id)
      transactions.value = transactions.value.filter((t) => t.id !== id)
      transactionsPagination.value.count--
    } catch (err: unknown) {
      error.value = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to delete transaction'
      throw err
    } finally {
      transactionsLoading.value = false
    }
  }

  // ==================== Utility Actions ====================

  /**
   * Load all essential data for inventory management
   */
  async function loadEssentialData() {
    await Promise.all([
      fetchCategories({ limit: 1000 }),
      fetchItems({ limit: 1000 }),
      fetchLocations({ limit: 1000 }),
      fetchStocks({ limit: 1000 })
    ])
  }

  function clearError() {
    error.value = null
  }

  function reset() {
    categories.value = []
    items.value = []
    currentItem.value = null
    variants.value = []
    locations.value = []
    currentLocation.value = null
    stocks.value = []
    transactions.value = []
    error.value = null
  }

  return {
    // State
    categories,
    categoriesLoading,
    categoriesPagination,
    items,
    currentItem,
    itemsLoading,
    itemsPagination,
    variants,
    variantsLoading,
    variantsPagination,
    locations,
    currentLocation,
    locationsLoading,
    locationsPagination,
    stocks,
    stocksLoading,
    stocksPagination,
    transactions,
    transactionsLoading,
    transactionsPagination,
    error,

    // Computed
    categoryOptions,
    locationOptions,
    memberLocations,
    storageLocations,
    itemOptions,
    memberLoans,

    // Actions - Categories
    fetchCategories,
    createCategory,
    updateCategory,
    deleteCategory,

    // Actions - Items
    fetchItems,
    fetchItem,
    createItem,
    updateItem,
    deleteItem,
    searchItems,

    // Actions - Variants
    fetchVariants,
    createVariant,
    updateVariant,
    deleteVariant,

    // Actions - Locations
    fetchLocations,
    fetchLocation,
    createLocation,
    updateLocation,
    deleteLocation,
    fetchLocationStock,

    // Actions - Stock
    fetchStocks,

    // Actions - Transactions
    fetchTransactions,
    createTransaction,
    deleteTransaction,

    // Utility
    loadEssentialData,
    clearError,
    reset
  }
})
