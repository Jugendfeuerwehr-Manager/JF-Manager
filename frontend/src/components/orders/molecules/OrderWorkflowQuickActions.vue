<template>
  <div :class="['workflow-actions', `workflow-actions--${layout}`]">
    <Button
      v-for="status in workflowStatuses"
      :key="status.id"
      class="workflow-actions__button"
      :class="{
        'is-active': status.isCurrent,
        'is-disabled': status.disabled
      }"
      :style="getButtonStyle(status)"
      :aria-label="status.label"
      :loading="loadingStatusId === status.id"
      :disabled="status.disabled || loadingStatusId !== null"
      size="small"
      :outlined="!status.isCurrent"
      @click="handleStatusClick(status.id)"
    >
      <span class="workflow-actions__label">
        {{ layout === 'full' ? status.label : status.shortLabel }}
      </span>
      <span v-if="status.count !== null" class="workflow-actions__count">
        {{ status.count }}
      </span>
    </Button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import { orderItemsApi } from '@/api/orderItems'
import { ordersApi } from '@/api/orders'
import { useOrderStatusStore } from '@/stores/orderStatus'
import type { Order, OrderItem } from '@/types/orders'

interface Props {
  order: Order
  layout?: 'compact' | 'full'
}

interface WorkflowStatusView {
  id: number
  label: string
  shortLabel: string
  color: string
  isCurrent: boolean
  count: number | null
  disabled: boolean
}

const props = withDefaults(defineProps<Props>(), {
  layout: 'compact'
})

const emit = defineEmits<{
  statusChanged: [orderId: number]
}>()

const toast = useToast()
const statusStore = useOrderStatusStore()
const loadingStatusId = ref<number | null>(null)
const itemsCache = ref<Record<number, OrderItem[]>>({})

const workflowStatuses = computed<WorkflowStatusView[]>(() => {
  return statusStore.sortedStatuses.map(status => {
    const summaryEntry = props.order.status_summary?.find(
      entry => entry.status_id === status.id
    )

    return {
      id: status.id,
      label: status.name,
      shortLabel: status.name.length > 10 ? status.name.slice(0, 10) + '…' : status.name,
      color: status.color,
      isCurrent: props.order.common_status?.id === status.id,
      count: summaryEntry?.count ?? null,
      disabled: props.order.common_status?.id === status.id
    }
  })
})

const getButtonStyle = (status: WorkflowStatusView) => {
  if (status.isCurrent) {
    return {
      backgroundColor: status.color,
      borderColor: status.color,
      color: getContrastColor(status.color)
    }
  }

  return {
    borderColor: status.color,
    color: status.color
  }
}

const ensureStatusesLoaded = async () => {
  if (!statusStore.sortedStatuses.length) {
    await statusStore.fetchActiveStatuses()
  }
}

const fetchOrderItems = async (): Promise<OrderItem[]> => {
  if (props.order.items && props.order.items.length > 0) {
    return props.order.items
  }

  if (itemsCache.value[props.order.id]) {
    return itemsCache.value[props.order.id]!
  }

  const response = await ordersApi.get(props.order.id)
  itemsCache.value[props.order.id] = response.data.items
  return itemsCache.value[props.order.id] ?? []
}

const handleStatusClick = async (statusId: number) => {
  await ensureStatusesLoaded()
  loadingStatusId.value = statusId

  try {
    const items = await fetchOrderItems()
    const itemIds = items
      .filter(item => item.status !== statusId)
      .map(item => item.id)

    if (!itemIds.length) {
      toast.add({
        severity: 'info',
        summary: 'Nichts zu aktualisieren',
        detail: 'Alle Artikel haben bereits diesen Status.',
        life: 2500
      })
      return
    }

    await orderItemsApi.bulkUpdateStatus({
      item_ids: itemIds,
      status: statusId
    })

    toast.add({
      severity: 'success',
      summary: 'Status aktualisiert',
      detail: `${itemIds.length} Artikel wurden angepasst.`,
      life: 2500
    })

    emit('statusChanged', props.order.id)
  } catch (error) {
    console.error('Workflow update failed', error)
    toast.add({
      severity: 'error',
      summary: 'Aktualisierung fehlgeschlagen',
      detail: 'Statusänderung konnte nicht durchgeführt werden.',
      life: 3000
    })
  } finally {
    loadingStatusId.value = null
  }
}

onMounted(async () => {
  await ensureStatusesLoaded()
})

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
.workflow-actions {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.workflow-actions--compact {
  justify-content: flex-end;
}

.workflow-actions--full {
  justify-content: flex-start;
}

.workflow-actions__button {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0 0.65rem;
  border-color: var(--surface-400);
}

.workflow-actions__button.is-active {
  background: var(--primary-color);
  color: var(--primary-color-text);
  border-color: transparent;
}

.workflow-actions__button.is-disabled {
  opacity: 0.6;
}

.workflow-actions__label {
  font-size: 0.8rem;
}

.workflow-actions__count {
  font-size: 0.75rem;
  font-weight: 600;
}

@media (max-width: 768px) {
  .workflow-actions {
    width: 100%;
  }

  .workflow-actions__button {
    flex: 1 1 calc(33% - 0.35rem);
    justify-content: center;
  }

  .workflow-actions__label {
    text-overflow: ellipsis;
    overflow: hidden;
    white-space: nowrap;
  }
}
</style>
