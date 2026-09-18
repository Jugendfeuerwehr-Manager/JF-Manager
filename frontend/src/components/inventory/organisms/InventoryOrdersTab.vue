<template>
  <div class="inventory-orders-tab">
    <div class="orders-stats">
      <Tag severity="info" :value="`${ordersCount} Bestellungen gesamt`" />
      <Tag v-if="newOrdersCount" severity="warning" :value="`${newOrdersCount} neue Eingänge`" />
    </div>

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
      @workflow-update="handleWorkflowUpdate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Tag from 'primevue/tag'
import OrdersList from '@/components/orders/organisms/OrdersList.vue'
import { useOrdersStore } from '@/stores/orders'
import { useOrderStatusStore } from '@/stores/orderStatus'
import type { OrderListParams } from '@/types/orders'

const router = useRouter()
const toast = useToast()
const ordersStore = useOrdersStore()
const statusStore = useOrderStatusStore()

const filters = ref<OrderListParams>({})

const orders = computed(() => ordersStore.orders)
const ordersCount = computed(() => ordersStore.ordersCount)
const loading = computed(() => ordersStore.loading)
const newOrdersCount = computed(() => orders.value.filter((order) => order.common_status?.code === 'NEW').length)

async function loadOrders() {
  try {
    await ordersStore.fetchOrders(filters.value)
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Bestellungen konnten nicht geladen werden', life: 3000 })
  }
}

function handleCreate() {
  router.push('/orders/create')
}

function handleQuickOrder() {
  router.push('/orders/quick')
}

function handleView(id: number) {
  router.push(`/orders/${id}`)
}

function handleEdit(id: number) {
  router.push(`/orders/${id}/edit`)
}

async function handleDelete(id: number) {
  try {
    await ordersStore.deleteOrder(id)
    toast.add({ severity: 'success', summary: 'Gelöscht', detail: 'Bestellung wurde gelöscht', life: 3000 })
    await loadOrders()
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Bestellung konnte nicht gelöscht werden', life: 3000 })
  }
}

async function handleWorkflowUpdate() {
  await loadOrders()
}

function handleFilter(newFilters: import('primevue/datatable').DataTableFilterEvent) {
  const filterParams: Partial<OrderListParams> = {}
  const filtersValue = newFilters.filters as Record<string, { value: string | null }>
  if (filtersValue.member_name?.value) {
    filterParams.search = filtersValue.member_name.value
  }
  filters.value = { ...filters.value, ...filterParams, offset: 0 }
  loadOrders()
}

function handlePage(event: { first: number; rows: number }) {
  filters.value = { ...filters.value, offset: event.first, limit: event.rows }
  loadOrders()
}

function handleSort(event: import('primevue/datatable').DataTableSortEvent) {
  let ordering = ''
  const sortField = event.sortField
  if (sortField && typeof sortField === 'string') {
    ordering = event.sortOrder === -1 ? `-${sortField}` : sortField
  }
  filters.value = { ...filters.value, ordering }
  loadOrders()
}

onMounted(async () => {
  await Promise.all([loadOrders(), ordersStore.fetchStatistics().catch(() => undefined), statusStore.fetchActiveStatuses().catch(() => undefined)])
})
</script>

<style scoped>
.inventory-orders-tab {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.orders-stats {
  display: flex;
  gap: 0.75rem;
}
</style>
