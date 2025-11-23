<template>
  <Card 
    class="order-card mobile-entity-card" 
    :class="{ 'cursor-pointer': clickable }"
    @click="handleClick"
  >
    <template #content>
      <div class="mobile-entity-card__header">
        <div>
          <h3 class="mobile-entity-card__title">#{{ order.id }} – {{ order.member_name }}</h3>
          <p class="mobile-entity-card__meta">
            {{ formatDate(order.order_date) }} · {{ order.items_count }} Artikel
          </p>
        </div>
        <OrderStatusBadge
          v-if="order.common_status"
          :status-name="order.common_status.name"
          :status-color="order.common_status.color"
          :status-code="order.common_status.code"
        />
      </div>

      <div class="mobile-entity-card__section" v-if="order.ordered_by_name">
        <div class="mobile-entity-card__row">
          <span class="mobile-entity-card__label">
            <i class="pi pi-user"></i>
            Bestellt von
          </span>
          <span class="mobile-entity-card__value">{{ order.ordered_by_name }}</span>
        </div>
      </div>

      <div
        v-if="showStatusBreakdown && order.status_summary?.length && shouldShowStatusBreakdown"
        class="order-status-tags"
      >
        <OrderStatusBadge
          v-for="status in order.status_summary"
          :key="status.status_id"
          :status-name="`${status.status_name}: ${status.count}`"
          :status-color="status.status_color"
          :status-code="status.status_code"
        />
      </div>

      <div class="mobile-entity-card__section" v-if="showItemsSummary && order.items_summary">
        <span class="mobile-entity-card__label">
          <i class="pi pi-shopping-bag"></i>
          Artikelübersicht
        </span>
        <p class="order-items-summary">
          {{ formatItemsSummary(order.items_summary) }}
        </p>
      </div>

      <div class="mobile-entity-card__section" v-if="showWorkflow" @click.stop>
        <OrderWorkflowQuickActions
          :order="order"
          layout="compact"
          @status-changed="handleWorkflowUpdate"
        />
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Card from 'primevue/card'
import OrderStatusBadge from '../atoms/OrderStatusBadge.vue'
import OrderWorkflowQuickActions from './OrderWorkflowQuickActions.vue'
import type { Order } from '@/types/orders'

interface Props {
  order: Order
  clickable?: boolean
  showWorkflow?: boolean
  showStatusBreakdown?: boolean
  showItemsSummary?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  clickable: true,
  showWorkflow: true,
  showStatusBreakdown: true,
  showItemsSummary: true
})

const emit = defineEmits<{
  click: [id: number]
  workflowUpdate: [id: number]
}>()

const handleClick = () => {
  if (props.clickable) {
    emit('click', props.order.id)
  }
}

const handleWorkflowUpdate = (orderId: number) => {
  emit('workflowUpdate', orderId)
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const formatItemsSummary = (items: any[]): string => {
  if (!items || items.length === 0) return 'Keine Artikel'
  
  const summary = items.map(item => {
    const size = item.size ? ` ${item.size}` : ''
    return `${item.quantity}x ${item.item_name}${size}`
  })
  
  return summary.join(', ')
}

const shouldShowStatusBreakdown = computed(() => {
  if (!props.order.status_summary?.length) {
    return false
  }

  if (!props.order.common_status) {
    return true
  }

  if (props.order.status_summary.length > 1) {
    return true
  }

  const onlyStatus = props.order.status_summary[0]
  return onlyStatus ? onlyStatus.status_id !== props.order.common_status.id : false
})
</script>

<style scoped>
.order-card {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.order-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.order-status-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin: 0.5rem 0;
}

.order-items-summary {
  margin: 0.25rem 0 0;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
  white-space: pre-wrap;
}
</style>
