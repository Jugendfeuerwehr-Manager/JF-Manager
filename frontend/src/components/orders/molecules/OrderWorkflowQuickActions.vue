<template>
  <div :class="['workflow-actions', `workflow-actions--${layout}`]">
    <span class="workflow-actions__label-text" v-if="layout === 'compact'">
      <i class="pi pi-refresh"></i> Workflow
    </span>
    
    <!-- Show all statuses in full mode (for OrdersList table) -->
    <template v-if="layout === 'full'">
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
          {{ status.label }}
        </span>
        <span v-if="status.count !== null" class="workflow-actions__count">
          {{ status.count }}
        </span>
      </Button>
    </template>

    <!-- Show next step + optional cancel in compact mode (for OrderCard) -->
    <template v-else>
      <!-- Primary action: Next workflow step -->
      <Button
        v-if="nextStep"
        :label="nextStep.label"
        :style="{
          backgroundColor: nextStep.color,
          borderColor: nextStep.color,
          color: getContrastColor(nextStep.color)
        }"
        :loading="loadingStatusId === nextStep.id"
        :disabled="loadingStatusId !== null"
        size="small"
        @click="handleStatusClick(nextStep.id)"
      />

      <!-- Split button for cancel if available and not the next step -->
      <Button
        v-if="cancelAction && (!nextStep || cancelAction.id !== nextStep.id)"
        :model="[
          {
            label: cancelAction.label,
            icon: 'pi pi-times-circle',
            command: () => cancelAction && handleStatusClick(cancelAction.id)
          }
        ]"
        icon="pi pi-ban"
        :style="{
          '--p-button-background': cancelAction.color,
          '--p-button-border-color': cancelAction.color,
          '--p-button-color': getContrastColor(cancelAction.color)
        }"
        :loading="loadingStatusId === cancelAction.id"
        :disabled="loadingStatusId !== null"
        size="small"
        severity="danger"
        outlined
      />

      <!-- Fallback if no actions available -->
      <span v-if="!nextStep && !cancelAction" class="workflow-actions__no-action">
        Keine Aktion verfügbar
      </span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import SplitButton from 'primevue/splitbutton'
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
  code: string
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

// Workflow transitions mapping (must match backend)
const WORKFLOW_TRANSITIONS: Record<string, string[]> = {
  'NEW': ['ORDERED', 'CANCELLED'],
  'pending': ['ORDERED', 'CANCELLED'],
  'ORDERED': ['RECEIVED', 'CANCELLED'],
  'ordered': ['RECEIVED', 'CANCELLED'],
  'RECEIVED': ['DELIVERED', 'CANCELLED'],
  'received': ['ready', 'defective'],
  'ready': ['delivered'],
  'delivered': [],
  'DELIVERED': [],
  'cancelled': [],
  'CANCELLED': [],
  'defective': ['ORDERED', 'CANCELLED']
}

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
      code: status.code,
      isCurrent: props.order.common_status?.id === status.id,
      count: summaryEntry?.count ?? null,
      disabled: props.order.common_status?.id === status.id
    }
  })
})

// Get available transition codes for current status
const availableTransitionCodes = computed<string[]>(() => {
  const currentCode = props.order.common_status?.code
  if (!currentCode) return []
  return WORKFLOW_TRANSITIONS[currentCode] || []
})

// Get available statuses (excluding cancel)
const availableStatuses = computed<WorkflowStatusView[]>(() => {
  return workflowStatuses.value.filter(status => 
    availableTransitionCodes.value.includes(status.code) &&
    !['CANCELLED', 'cancelled'].includes(status.code)
  )
})

// Get next logical step (first non-cancel transition)
const nextStep = computed<WorkflowStatusView | null>(() => {
  return availableStatuses.value[0] || null
})

// Get cancel action if available
const cancelAction = computed<WorkflowStatusView | null>(() => {
  const cancelCodes = ['CANCELLED', 'cancelled']
  if (!availableTransitionCodes.value.some(code => cancelCodes.includes(code))) {
    return null
  }
  
  return workflowStatuses.value.find(status => 
    cancelCodes.includes(status.code)
  ) || null
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
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.workflow-actions__label-text {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.35rem;
  white-space: nowrap;
}

.workflow-actions__label-text i {
  font-size: 0.75rem;
}

.workflow-actions--compact {
  justify-content: flex-start;
}

.workflow-actions--full {
  justify-content: flex-start;
}

.workflow-actions__button {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0 0.65rem;
  transition: all 0.2s ease;
  font-size: 0.8rem;
  height: 2rem;
  min-width: fit-content;
}

.workflow-actions__button.is-active {
  font-weight: 600;
}

.workflow-actions__button.is-disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.workflow-actions__label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.workflow-actions__count {
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 1rem;
  padding: 0.1rem 0.4rem;
  font-size: 0.7rem;
  font-weight: 600;
  min-width: 1.2rem;
  text-align: center;
}

.workflow-actions__no-action {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
  font-style: italic;
  padding: 0.35rem 0.5rem;
}

/* Split button styling for cancel action */
:deep(.p-splitbutton) {
  height: 2rem;
}

:deep(.p-splitbutton .p-button) {
  height: 2rem;
  font-size: 0.8rem;
}

:deep(.p-splitbutton-menubutton) {
  padding: 0 0.4rem;
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
