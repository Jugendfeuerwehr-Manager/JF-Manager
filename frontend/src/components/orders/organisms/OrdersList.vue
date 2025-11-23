<template>
  <!-- Header -->
    <Toolbar class="mb-4">
          <template #start>
            <h2>Bestellungen</h2> 
          </template>

          <template #end>
            <div class="flex gap-2">
            <SendSummaryAction
              :new-orders-count="newOrdersCount"
              />
            <Button
            label="Schnellbestellung"
            icon="pi pi-bolt"
            severity="secondary"
            @click="$emit('quickOrder')"
          />
          <Button
            label="Neue Bestellung"
            icon="pi pi-plus"
            @click="$emit('create')"
          />
            </div>
          </template>
      </Toolbar>

    <!-- Desktop Table -->
    <DataTable
      v-if="!isMobile"
      :value="orders"
      :loading="loading"
      :rows="pageSize"
      :total-records="ordersCount"
      :paginator="showPagination"
      :lazy="true"
      @page="handlePageChange"
      @sort="handleSort"
      stripedRows
      showGridlines
      filterDisplay="row"
      v-model:filters="filters"
      @filter="handleFilter"
      paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink RowsPerPageDropdown CurrentPageReport"
      current-page-report-template="{first} bis {last} von {totalRecords}"
      :rows-per-page-options="[10, 25, 50]"
    >
      <template #empty>
        <div class="text-center p-4">
          <i class="pi pi-shopping-cart text-4xl text-400 mb-3"></i>
          <p class="text-500">Keine Bestellungen gefunden</p>
          <Button
            label="Neue Bestellung erstellen"
            icon="pi pi-plus"
            size="small"
            @click="$emit('create')"
          />
        </div>
      </template>

      <Column field="id" header="ID" :sortable="true" style="width: 80px">
        <template #body="{ data }">
          <strong>#{{ data.id }}</strong>
        </template>
      </Column>

      <Column field="member_name" header="Mitglied" :sortable="true" :showFilterMenu="false">
        <template #filter="{ filterModel, filterCallback }">
          <InputText
            v-model="filterModel.value"
            type="text"
            @input="filterCallback()"
            placeholder="Suchen nach Name"
            class="p-column-filter"
          />
        </template>
        <template #body="{ data }">
          <div>
            <div class="font-semibold">{{ data.member_name }}</div>
          </div>
        </template>
      </Column>

      <Column field="order_date" header="Datum" :sortable="true" style="width: 180px">
        <template #body="{ data }">
          {{ formatDate(data.order_date) }}
        </template>
      </Column>

      <Column header="Artikel" style="width: 300px">
        <template #body="{ data }">
          <div class="text-sm">
            {{ formatItemsSummary(data.items_summary) }}
          </div>
        </template>
      </Column>

      <Column header="Status" style="width: 250px">
        <template #body="{ data }">
          <div class="flex flex-wrap gap-1">
            <Tag
              v-for="status in data.status_summary"
              :key="status.status_id"
              :value="`${status.status_name}: ${status.count}`"
              :style="{
                backgroundColor: status.status_color,
                color: getContrastColor(status.status_color)
              }"
              class="text-xs"
            />
          </div>
        </template>
      </Column>

      <Column header="Workflow" style="min-width: 220px">
        <template #body="{ data }">
          <OrderWorkflowQuickActions
            :order="data"
            layout="compact"
            @status-changed="handleWorkflowUpdate"
          />
        </template>
      </Column>

      <Column field="ordered_by_name" header="Bestellt von" :sortable="true" style="width: 150px">
        <template #body="{ data }">
          {{ data.ordered_by_name }}
        </template>
      </Column>

      <Column header="Aktionen" :exportable="false" style="width: 150px">
        <template #body="{ data }">
          <div class="flex gap-1">
            <Button
              icon="pi pi-eye"
              size="small"
              text
              rounded
              @click="$emit('view', data.id)"
              v-tooltip.top="'Details anzeigen'"
            />
            <Button
              icon="pi pi-pencil"
              size="small"
              text
              rounded
              severity="secondary"
              @click="$emit('edit', data.id)"
              v-tooltip.top="'Bearbeiten'"
            />
            <Button
              icon="pi pi-trash"
              size="small"
              text
              rounded
              severity="danger"
              @click="$emit('delete', data.id)"
              v-tooltip.top="'Löschen'"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <!-- Mobile Cards -->
    <div v-else class="mobile-orders-list">
      <ResponsiveList
        :items="orders"
        :loading="loading"
        :rows="pageSize"
        :total-records="ordersCount"
        :paginator="showPagination && ordersCount > pageSize"
        :lazy="true"
        item-key="id"
        @page="handlePageChange"
      >
        <template #item="{ item: order }">
          <OrderCard
            :order="order"
            @click="$emit('view', order.id)"
            @workflow-update="handleWorkflowUpdate"
          />
        </template>

        <template #empty>
          <div class="mobile-list-empty">
            <i class="pi pi-shopping-cart"></i>
            <p>Keine Bestellungen gefunden</p>
          </div>
        </template>
      </ResponsiveList>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import type { Order } from '@/types/orders'
import type { DataTablePageEvent, DataTableSortEvent, DataTableFilterEvent } from 'primevue/datatable'
import type { DataViewPageEvent } from 'primevue/dataview'
import { Toolbar } from 'primevue'

import ResponsiveList from '@/components/common/ResponsiveList.vue'
import SendSummaryAction from '../molecules/SendSummaryAction.vue'
import OrderWorkflowQuickActions from '../molecules/OrderWorkflowQuickActions.vue'
import OrderCard from '../molecules/OrderCard.vue'
import OrderStatusBadge from '../atoms/OrderStatusBadge.vue'

const FilterMatchMode = {
  CONTAINS: 'contains'
}

interface Props {
  orders: Order[]
  ordersCount: number
  newOrdersCount?: number
  loading?: boolean
  showPagination?: boolean
  pageSize?: number
}

const props = withDefaults(defineProps<Props>(), {
  newOrdersCount: 0,
  loading: false,
  showPagination: true,
  pageSize: 25
})

const emit = defineEmits<{
  create: []
  quickOrder: []
  sendSummary: []
  view: [id: number]
  edit: [id: number]
  delete: [id: number]
  filter: [filters: any]
  page: [event: DataTablePageEvent | DataViewPageEvent]
  sort: [event: DataTableSortEvent]
  workflowUpdate: [orderId: number]
}>()

const filters = ref({
  member_name: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

const isMobile = ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false)

const handleResize = () => {
  if (typeof window === 'undefined') return
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

function formatItemsSummary(items: any[]): string {
  if (!items || items.length === 0) return 'Keine Artikel'
  
  const summary = items.map(item => {
    const size = item.size ? ` ${item.size}` : ''
    return `${item.quantity}x ${item.item_name}${size}`
  })
  
  return summary.join(', ')
}

function handlePageChange(event: DataTablePageEvent | DataViewPageEvent) {
  emit('page', event)
}

function handleSort(event: DataTableSortEvent) {
  emit('sort', event)
}

function handleFilter(event: DataTableFilterEvent) {
  emit('filter', event.filters)
}

function handleWorkflowUpdate(orderId: number) {
  emit('workflowUpdate', orderId)
}

function getContrastColor(color?: string) {
  if (!color) return '#fff'
  const hex = color.replace('#', '')
  const normalized = hex.length === 3 ? hex.split('').map(char => char + char).join('') : hex.padEnd(6, '0')
  const r = parseInt(normalized.slice(0, 2), 16) || 0
  const g = parseInt(normalized.slice(2, 4), 16) || 0
  const b = parseInt(normalized.slice(4, 6), 16) || 0
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
  return luminance > 186 ? '#333' : '#fff'
}
</script>

<style scoped>
.mobile-orders-list {
  margin-top: 1rem;
}
</style>
