<template>
  <div class="orders-view">
    <div class="view-container">
      <!-- Orders List -->
      <OrdersList
        :orders="orders"
        :orders-count="ordersCount"
        :new-orders-count="newOrdersCount"
        :loading="loading"
        @create="handleCreate"
        @quick-order="handleQuickOrder"
        @view="handleView"
        @edit="handleEdit"
        @delete="handleDelete"
        @filter="handleFilter"
        @page="handlePage"
        @sort="handleSort"
      >
        <template #header-actions>
          <SendSummaryAction
            :new-orders-count="newOrdersCount"
            @success="handleSendSuccess"
            @error="handleSendError"
          />
        </template>
      </OrdersList>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import OrdersList from '@/components/orders/organisms/OrdersList.vue'
import SendSummaryAction from '@/components/orders/molecules/SendSummaryAction.vue'
import { useOrdersStore } from '@/stores/orders'
import { useOrderStatusStore } from '@/stores/orderStatus'
import { ordersApi } from '@/api/orders'
import type { OrderListParams } from '@/types/orders'
const router = useRouter()
const toast = useToast()
const ordersStore = useOrdersStore()
const statusStore = useOrderStatusStore()

// State
const filters = ref<OrderListParams>({})

// Computed
const orders = computed(() => ordersStore.orders)
const ordersCount = computed(() => ordersStore.ordersCount)
const loading = computed(() => ordersStore.loading)
const statistics = computed(() => ordersStore.statistics)

// Calculate NEW orders count
const newOrdersCount = computed(() => {
  return orders.value.filter(order => order.common_status?.code === 'NEW').length
})

// Methods
const loadOrders = async () => {
  try {
    await ordersStore.fetchOrders(filters.value)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Bestellungen konnten nicht geladen werden',
      life: 3000
    })
  }
}

const loadStatistics = async () => {
  try {
    await ordersStore.fetchStatistics()
  } catch (error) {
    console.error('Failed to load statistics:', error)
  }
}

const loadStatuses = async () => {
  try {
    await statusStore.fetchActiveStatuses()
  } catch (error) {
    console.error('Failed to load statuses:', error)
  }
}

const handleCreate = () => {
  router.push('/orders/create')
}

const handleQuickOrder = () => {
  router.push('/orders/quick')
}

const handleView = (id: number) => {
  router.push(`/orders/${id}`)
}

const handleEdit = (id: number) => {
  router.push(`/orders/${id}/edit`)
}

const handleDelete = async (id: number) => {
  // TODO: Add confirmation dialog
  try {
    await ordersStore.deleteOrder(id)
    toast.add({
      severity: 'success',
      summary: 'Gelöscht',
      detail: 'Bestellung wurde gelöscht',
      life: 3000
    })
    await loadOrders()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Bestellung konnte nicht gelöscht werden',
      life: 3000
    })
  }
}

const handleSendSuccess = async () => {
  // Reload orders to reflect status changes
  await loadOrders()
}

const handleSendError = (error: any) => {
  console.error('Error sending summary:', error)
}

const handleFilter = (newFilters: any) => {
  // Extract filter values from PrimeVue filter object
  const filterParams: any = {}
  
  if (newFilters.member_name?.value) {
    filterParams.search = newFilters.member_name.value
  }
  
  filters.value = { ...filters.value, ...filterParams, offset: 0 }
  loadOrders()
}

const handlePage = (event: any) => {
  filters.value = {
    ...filters.value,
    offset: event.first,
    limit: event.rows
  }
  loadOrders()
}

const handleSort = (event: any) => {
  // Map PrimeVue sort to Django ordering
  let ordering = ''
  
  if (event.sortField) {
    ordering = event.sortOrder === -1 ? `-${event.sortField}` : event.sortField
  }
  
  filters.value = { ...filters.value, ordering }
  loadOrders()
}



// Lifecycle
onMounted(async () => {
  await Promise.all([
    loadOrders(),
    loadStatistics(),
    loadStatuses()
  ])
})
</script>

<style scoped>
.orders-view {
  animation: fadeIn 0.3s ease;
}

.view-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}


.stat-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: white;
}

.stat-icon.bg-primary {
  background: var(--primary-color);
}

.stat-icon.bg-warning {
  background: #f59e0b;
}

.stat-icon.bg-success {
  background: #10b981;
}

.stat-icon.bg-info {
  background: #3b82f6;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  font-weight: 500;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-color);
  line-height: 1;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .stat-value {
    font-size: 1.5rem;
  }
}
</style>
