<template>
  <div class="services-list-container">
    <StateView v-if="loading && (!services || services.length === 0)" kind="loading" title="Dienste werden geladen …" />

    <StateView v-else-if="error" kind="error" title="Dienste konnte nicht geladen werden" :message="error" :retry="false" />

    <StateView v-else-if="!services || services.length === 0" kind="empty" :title="emptyTitle" :message="emptyMessage">
      <slot name="empty-actions" />
    </StateView>

    <DataView
      v-else
      :value="services"
      :loading="loading"
      :paginator="totalRecords > pageSize"
      :rows="pageSize"
      :totalRecords="totalRecords"
      :first="(currentPage - 1) * pageSize"
      :rowsPerPageOptions="[12, 24, 48]"
      :lazy="true"
      @page="handlePageChange"
    >
      <template #list="slotProps">
        <div class="services-list">
          <section v-for="group in groupByMonth(slotProps.items)" :key="group.key" class="month" :aria-label="group.label">
            <h2 class="month__label">{{ group.label }}</h2>
            <div class="month__items">
              <ServiceListItem
                v-for="service in group.items"
                :key="service.id"
                :service="service"
                :show-actions="showActions"
                @view="(id) => $emit('view', id)"
                @edit="(id) => $emit('edit', id)"
                @open-training="(trainingId) => $emit('open-training', trainingId)"
              />
            </div>
          </section>
        </div>
      </template>
    </DataView>
  </div>
</template>

<script setup lang="ts">
import DataView from 'primevue/dataview'
import StateView from '@/components/common/StateView.vue'
import ServiceListItem from '../molecules/ServiceListItem.vue'
import type { Service } from '@/types/servicebook'
import type { PageState } from 'primevue/paginator'

interface Props {
  services: Service[]
  loading?: boolean
  error?: string | null
  totalRecords?: number
  currentPage?: number
  pageSize?: number
  showActions?: boolean
  emptyTitle?: string
  emptyMessage?: string
}

interface Emits {
  (e: 'view', id: number): void
  (e: 'edit', id: number): void
  (e: 'create'): void
  (e: 'open-training', trainingId: number): void
  (e: 'page-change', page: number, pageSize: number): void
}

withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
  totalRecords: 0,
  currentPage: 1,
  pageSize: 12,
  showActions: true,
  emptyTitle: 'Keine Dienste gefunden',
  emptyMessage: '',
})

const emit = defineEmits<Emits>()

/** Keeps the server order (upcoming ascending, past descending) and starts a heading per month. */
function groupByMonth(items: Service[]) {
  const groups: { key: string; label: string; items: Service[] }[] = []
  for (const service of items) {
    const start = new Date(service.start)
    const key = `${start.getFullYear()}-${start.getMonth()}`
    let group = groups[groups.length - 1]
    if (!group || group.key !== key) {
      group = { key, label: start.toLocaleDateString('de-DE', { month: 'long', year: 'numeric' }), items: [] }
      groups.push(group)
    }
    group.items.push(service)
  }
  return groups
}

const handlePageChange = (event: PageState) => {
  const newPage = Math.floor(event.first / event.rows) + 1
  emit('page-change', newPage, event.rows)
}
</script>

<style scoped>
.services-list {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.month {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
}

.month__label {
  margin: 0 var(--jf-space-0-5);
  font-size: 0.8125rem;
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--jf-color-text-muted);
}

.month__items {
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  overflow: hidden;
}

.month__items > * + * {
  border-top: 1px solid var(--jf-color-border);
}

.services-list-container :deep(.p-dataview-content),
.services-list-container :deep(.p-dataview) {
  background: transparent;
}
</style>
