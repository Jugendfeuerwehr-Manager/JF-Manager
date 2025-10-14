<template>
  <div class="service-list-item">
    <!-- Header Row: Icon + Topic -->
    <div class="item-header">
      
      <h3 class="service-title">{{ service.topic || 'Kein Thema' }}</h3>
      <Tag
        v-if="service.has_events"
        severity="warn"
        icon="pi pi-exclamation-triangle"
        class="mr-2"
      />
    </div>

    <!-- Details Row: Date, Place, Manager, Attendance, Actions -->
    <div class="item-details">
      <!-- Date Column -->
      <div class="col-date">
        <ServiceDateDisplay :start="service.start" :end="service.end" />
      </div>

      <!-- Place Column -->
      <div class="col-place">
        <div v-if="service.place" class="service-meta">
          <i class="pi pi-map-marker"></i>
          <span>{{ service.place }}</span>
        </div>
      </div>

      <!-- Operations Manager Column -->
      <div class="col-manager">
        <div v-if="service.operations_manager && service.operations_manager.length > 0" class="service-meta">
          <i class="pi pi-user"></i>
          <span>{{ operationsManagerNames }}</span>
        </div>
      </div>

      <!-- Attendance Stats Column -->
      <div class="col-attendance">
        <AttendanceStatsDisplay 
          v-if="service.attendance_summary"
          :summary="service.attendance_summary" 
        />
      </div>

      <!-- Actions Column -->
      <div v-if="showActions" class="col-actions">
        <Button
          label="Bearbeiten"
          icon="pi pi-pencil"
          outlined
          size="small"
          @click="$emit('edit', service.id)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
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
  return props.service.operations_manager?.map((m) => m.full_name).join(', ') || ''
})
</script>

<style scoped>
.service-list-item {
  display: flex;
  flex-direction: column;
  padding: 1rem;

  border-bottom: 1px solid var(--p-menu-border-color);
  gap: 0.75rem;
}

/* Header Row: Icon + Topic */
.item-header {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 0.5rem;
}

.service-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-color);
  flex: 1;
}

/* Details Row: Grid layout for aligned columns */
.item-details {
  display: grid;
  grid-template-columns: 180px 1.5fr 1.5fr 140px auto;
  gap: 1rem;
  align-items: center;
}

.col-date {
  font-size: 0.9rem;
}

.col-place,
.col-manager {
  overflow: hidden;
}

.service-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-color-secondary);
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
}

.service-meta span {
  overflow: hidden;
  text-overflow: ellipsis;
}

.service-meta i {
  color: var(--primary-color);
  flex-shrink: 0;
}

.col-attendance {
  display: flex;
  justify-content: flex-start;
}

.col-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
  flex-shrink: 0;
}

/* Mobile responsive - stack vertically */
@media (max-width: 1024px) {
  .item-details {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .col-actions {
    justify-content: flex-start;
  }
  .col-attendance {
    justify-content: center;
  }
  .col-actions {
    justify-content: flex-end;
  }
}
</style>
