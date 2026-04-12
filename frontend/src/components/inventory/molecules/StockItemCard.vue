<template>
  <Card class="stock-item-card">
    <template #content>
      <div class="card-content">
        <div class="item-info">
          <div class="item-header">
            <span class="item-name">{{ displayName }}</span>
            <Tag v-if="stock.category_id" :value="categoryName" severity="secondary" />
          </div>
          <div class="item-location">
            <i class="pi pi-map-marker"></i>
            {{ stock.location_name }}
          </div>
        </div>
        <div class="item-quantity">
          <StockBadge :quantity="stock.quantity" />
        </div>
        <div class="item-actions">
          <Button
            icon="pi pi-arrow-right"
            size="small"
            text
            rounded
            severity="info"
            title="Umlagern"
            @click="$emit('move', stock)"
          />
          <Button
            icon="pi pi-user"
            size="small"
            text
            rounded
            severity="primary"
            title="Ausleihen"
            @click="$emit('loan', stock)"
          />
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import StockBadge from '../atoms/StockBadge.vue'
import type { Stock } from '@/types/inventory'
import { useInventoryStore } from '@/stores/inventory'

interface Props {
  stock: Stock
}

const props = defineProps<Props>()

defineEmits<{
  move: [stock: Stock]
  loan: [stock: Stock]
}>()

const inventoryStore = useInventoryStore()

const displayName = computed(() => {
  return props.stock.variant_display || props.stock.item_name || 'Unbekannter Artikel'
})

const categoryName = computed(() => {
  const category = inventoryStore.categories.find((c) => c.id === props.stock.category_id)
  return category?.name || ''
})
</script>

<style scoped>
.stock-item-card {
  margin-bottom: 0.5rem;
}

.card-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.item-name {
  font-weight: 600;
  color: var(--text-color);
}

.item-location {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin-top: 0.25rem;
}

.item-quantity {
  padding: 0 1rem;
}

.item-actions {
  display: flex;
  gap: 0.25rem;
}
</style>
