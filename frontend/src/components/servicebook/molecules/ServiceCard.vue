<template>
  <Card class="service-card">
    <template #content>
      <div class="service-card-header">
        <div class="service-title-row">
          <h3 class="service-title">
            <Tag v-if="service.has_events" severity="warn" icon="pi pi-exclamation-triangle" class="mr-2" />
            {{ service.topic || 'Kein Thema' }}
          </h3>
        </div>
        <ServiceDateDisplay :start="service.start" :end="service.end" />
      </div>

      <div v-if="service.place" class="service-meta">
        <i class="pi pi-map-marker"></i>
        <span>{{ service.place }}</span>
      </div>

      <div v-if="service.operations_manager.length > 0" class="service-meta">
        <i class="pi pi-user"></i>
        <span>{{ operationsManagerNames }}</span>
      </div>

      <Divider />

      <AttendanceStatsDisplay :summary="service.attendance_summary" />

      <template v-if="showActions">
        <Divider />
        <div class="service-actions">
          <Button
            label="Bearbeiten"
            icon="pi pi-pencil"
            outlined
            size="small"
            @click="$emit('edit', service.id)"
          />
          <Button
            label="Details"
            icon="pi pi-eye"
            size="small"
            @click="$emit('view', service.id)"
          />
        </div>
      </template>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'
import ServiceDateDisplay from '../atoms/ServiceDateDisplay.vue'
import AttendanceStatsDisplay from './AttendanceStatsDisplay.vue'
import type { Service } from '@/types/servicebook'

interface Props {
  service: Service
  showActions?: boolean
}

interface Emits {
  (e: 'view', id: number): void
  (e: 'edit', id: number): void
}

const props = withDefaults(defineProps<Props>(), {
  showActions: true
})

const emit = defineEmits<Emits>()

const operationsManagerNames = computed(() => {
  return props.service.operations_manager.map((m) => m.full_name).join(', ')
})
</script>

<style scoped>
.service-card {
  height: 100%;
}


.service-card-header {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1rem;
}

.service-title-row {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.service-title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-color);
  flex: 1;
}

.service-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  margin-bottom: 0.5rem;
}

.service-meta i {
  color: var(--primary-color);
}

.service-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}
</style>
