<template>
  <div class="order-card" @click="handleClick">
    <Card :class="{ 'cursor-pointer': clickable }">
      <template #header v-if="showHeader">
        <div class="order-card-header">
          <div class="order-info">
            <h3 class="order-title">
              <i class="pi pi-shopping-cart"></i>
              Bestellung #{{ order.id }}
            </h3>
            <div class="order-meta">
              <span class="member-name">
                <i class="pi pi-user"></i>
                {{ order.member_name }}
              </span>
              <span class="member-group" v-if="order.member_group">
                <i class="pi pi-users"></i>
                {{ order.member_group }}
              </span>
            </div>
          </div>
          <OrderStatusBadge
            v-if="order.common_status"
            :status-name="order.common_status.name"
            :status-color="order.common_status.color"
            :status-code="order.common_status.code"
          />
        </div>
      </template>

      <template #content>
        <div class="order-details">
          <div class="detail-row">
            <span class="detail-label">
              <i class="pi pi-calendar"></i>
              Datum:
            </span>
            <span class="detail-value">
              {{ formatDate(order.order_date) }}
            </span>
          </div>

          <div class="detail-row">
            <span class="detail-label">
              <i class="pi pi-box"></i>
              Artikel:
            </span>
            <span class="detail-value">
              {{ order.items_count }}
            </span>
          </div>

          <div class="detail-row" v-if="order.ordered_by_name">
            <span class="detail-label">
              <i class="pi pi-user-edit"></i>
              Bestellt von:
            </span>
            <span class="detail-value">
              {{ order.ordered_by_name }}
            </span>
          </div>

          <div class="detail-row" v-if="order.notes && showNotes">
            <span class="detail-label">
              <i class="pi pi-comment"></i>
              Bemerkung:
            </span>
            <span class="detail-value">
              {{ order.notes }}
            </span>
          </div>

          <!-- Status Summary -->
          <div class="status-summary" v-if="showStatusSummary && order.status_summary && order.status_summary.length > 0">
            <Divider />
            <div class="summary-title">Status Übersicht:</div>
            <div class="summary-items">
              <div 
                v-for="summary in order.status_summary" 
                :key="summary.status_id"
                class="summary-item"
              >
                <OrderStatusBadge
                  :status-name="summary.status_name"
                  :status-color="summary.status_color"
                  :status-code="summary.status_code"
                />
                <Badge :value="summary.count" />
              </div>
            </div>
          </div>
        </div>
      </template>

      <template #footer v-if="showActions">
        <div class="order-actions">
          <Button
            label="Details"
            icon="pi pi-eye"
            @click.stop="$emit('view', order.id)"
            text
          />
          <Button
            label="Bearbeiten"
            icon="pi pi-pencil"
            @click.stop="$emit('edit', order.id)"
            text
            v-if="canEdit"
          />
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import Divider from 'primevue/divider'
import OrderStatusBadge from '../atoms/OrderStatusBadge.vue'
import type { Order } from '@/types/orders'

interface Props {
  order: Order
  clickable?: boolean
  showHeader?: boolean
  showNotes?: boolean
  showStatusSummary?: boolean
  showActions?: boolean
  canEdit?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  clickable: true,
  showHeader: true,
  showNotes: true,
  showStatusSummary: true,
  showActions: true,
  canEdit: true
})

const emit = defineEmits<{
  click: [id: number]
  view: [id: number]
  edit: [id: number]
}>()

const handleClick = () => {
  if (props.clickable) {
    emit('click', props.order.id)
  }
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.order-card {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.cursor-pointer {
  cursor: pointer;
  transition: all 0.2s ease;
}

.cursor-pointer:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.order-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem;
  background: linear-gradient(135deg, var(--surface-50) 0%, var(--surface-100) 100%);
  border-bottom: 1px solid var(--surface-border);
}

.order-info {
  flex: 1;
}

.order-title {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  color: var(--primary-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.order-meta {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.member-name,
.member-group {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.order-details {
  padding: 0.5rem 0;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--surface-border);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  color: var(--text-color-secondary);
}

.detail-value {
  color: var(--text-color);
  text-align: right;
}

.status-summary {
  margin-top: 0.5rem;
}

.summary-title {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.summary-items {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.order-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-border);
}

/* Mobile responsive */
@media (max-width: 768px) {
  .order-card-header {
    flex-direction: column;
    gap: 1rem;
  }

  .order-meta {
    flex-direction: column;
    gap: 0.5rem;
  }

  .detail-row {
    flex-direction: column;
    gap: 0.25rem;
  }

  .detail-value {
    text-align: left;
  }
}
</style>
