<template>
  <div class="responsive-list-wrapper">
    <DataView
      :value="items"
      layout="list"
      :loading="loading"
      :paginator="paginator"
      :rows="rows"
      :total-records="totalRecords"
      :lazy="lazy"
      :data-key="itemKey"
      @page="onPage"
      class="responsive-list"
    >
      <template #list="slotProps">
        <div class="mobile-list-grid">
          <template v-if="slotProps.items && slotProps.items.length">
            <template
              v-for="item in slotProps.items"
              :key="resolveKey(item)"
            >
              <slot name="item" :item="item" />
            </template>
          </template>
          <div v-else class="mobile-list-empty">
            <slot name="empty">
              <i class="pi pi-inbox"></i>
              <p>Keine Einträge gefunden</p>
            </slot>
          </div>
        </div>
      </template>
    </DataView>
  </div>
</template>

<script setup lang="ts">
import DataView from 'primevue/dataview'
import type { DataViewPageEvent } from 'primevue/dataview'

interface Props {
  items: unknown[]
  loading?: boolean
  rows?: number
  paginator?: boolean
  totalRecords?: number
  lazy?: boolean
  itemKey?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  rows: 20,
  paginator: false,
  totalRecords: 0,
  lazy: false,
  itemKey: 'id'
})

const emit = defineEmits<{
  page: [event: DataViewPageEvent]
}>()

const onPage = (event: DataViewPageEvent) => {
  emit('page', event)
}

const resolveKey = (item: Record<string, unknown>) => {
  const key = props.itemKey
  if (item && Object.prototype.hasOwnProperty.call(item, key)) {
    return (item as Record<string, unknown>)[key] as string | number
  }
  return JSON.stringify(item)
}
</script>

<style scoped>
.responsive-list-wrapper {
  width: 100%;
}

.mobile-list-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

@media (max-width: 768px) {
  .mobile-list-grid {
    gap: 0.75rem;
  }
}

.mobile-list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  gap: 0.5rem;
  color: var(--text-color-secondary);
}

.mobile-list-empty i {
  font-size: 2rem;
}

.mobile-list-empty p {
  margin: 0;
  font-weight: 500;
}
</style>
