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
              <StateView kind="empty" title="Keine Einträge gefunden" message="Passe Suche oder Filter an oder lege einen neuen Eintrag an." />
            </slot>
          </div>
        </div>
      </template>
      <template #empty>
        <slot name="empty">
          <StateView kind="empty" title="Keine Einträge gefunden" message="Passe Suche oder Filter an oder lege einen neuen Eintrag an." />
        </slot>
      </template>
    </DataView>
  </div>
</template>

<script setup lang="ts">
import DataView from 'primevue/dataview'
import StateView from './StateView.vue'
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
  gap: var(--jf-space-2);
}

.responsive-list :deep(.p-dataview-content),
.responsive-list :deep(.p-dataview-emptymessage) {
  background: transparent;
}

@media (max-width: 768px) {
  .mobile-list-grid {
    gap: var(--jf-space-1-5);
  }
}

.mobile-list-empty {
  display: block;
}
</style>
