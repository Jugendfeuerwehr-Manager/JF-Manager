<template>
  <div class="services-list-container">
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <!-- Error State -->
    <Message v-else-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <!-- Empty State -->
    <div v-else-if="!services || services.length === 0" class="empty-state">
      <i class="pi pi-book empty-icon"></i>
      <h3>Keine Dienste gefunden</h3>
      <p>Erstellen Sie einen neuen Dienst, um zu beginnen.</p>
      <Button label="Neuer Dienst" icon="pi pi-plus" @click="$emit('create')" />
    </div>

    <!-- Services DataView -->
    <DataView
      v-else
      :value="services"
      :paginator="totalRecords > pageSize"
      :rows="pageSize"
      :totalRecords="totalRecords"
      :first="(currentPage - 1) * pageSize"
      :rowsPerPageOptions="[12, 24, 48]"
      @page="handlePageChange"
    >
      <template #list="slotProps">
        <div class="services-list">
          <div
            v-for="(service, index) in slotProps.items"
            :key="service.id"
            :class="{ 'border-top': index !== 0 }"
          >
            <ServiceListItem
              :service="service"
              :show-actions="showActions"
              @view="(id) => $emit('view', id)"
              @edit="(id) => $emit('edit', id)"
            />
          </div>
        </div>
      </template>
    </DataView>
  </div>
</template>

<script setup lang="ts">
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Button from 'primevue/button'
import DataView from 'primevue/dataview'
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
}

interface Emits {
  (e: 'view', id: number): void
  (e: 'edit', id: number): void
  (e: 'create'): void
  (e: 'page-change', page: number, pageSize: number): void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
  totalRecords: 0,
  currentPage: 1,
  pageSize: 12,
  showActions: true
})

const emit = defineEmits<Emits>()

const handlePageChange = (event: PageState) => {
  const newPage = Math.floor(event.first / event.rows) + 1
  emit('page-change', newPage, event.rows)
}
</script>

<style scoped>


/* List View Styles */
</style>
