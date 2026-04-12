<template>
  <Card class="special-task-card">
    <template #content>
      <div class="card-body">
        <div class="card-header-section">
          <div class="person-info">
            <h6 class="person-name">{{ specialTask.person_name }}</h6>
            <Chip :label="specialTask.task_name" class="task-chip" />
          </div>
          <SpecialTaskStatusBadge :is-active="specialTask.is_active" />
        </div>

        <div class="card-details">
          <div class="detail-row">
            <span class="detail-label">
              <i class="pi pi-calendar"></i>
              Start:
            </span>
            <span class="detail-value">{{ formatDate(specialTask.start_date) }}</span>
          </div>

          <div class="detail-row">
            <span class="detail-label">
              <i class="pi pi-calendar-times"></i>
              Ende:
            </span>
            <span class="detail-value">{{
              specialTask.end_date ? formatDate(specialTask.end_date) : 'Noch aktiv'
            }}</span>
          </div>

          <div class="detail-row">
            <span class="detail-label">
              <i class="pi pi-clock"></i>
              Dauer:
            </span>
            <span class="detail-value">{{ specialTask.duration_days }} Tage</span>
          </div>
        </div>

        <div v-if="showActions" class="card-actions">
          <Button
            icon="pi pi-eye"
            label="Details"
            size="small"
            text
            @click="emit('view', specialTask.id)"
          />
          <Button
            v-if="specialTask.is_active"
            icon="pi pi-check"
            label="Beenden"
            size="small"
            text
            severity="warning"
            @click="emit('end', specialTask.id)"
          />
          <Button
            icon="pi pi-pencil"
            label="Bearbeiten"
            size="small"
            text
            @click="emit('edit', specialTask.id)"
          />
          <Button
            icon="pi pi-trash"
            label="Löschen"
            size="small"
            text
            severity="danger"
            @click="emit('delete', specialTask.id)"
          />
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import Card from 'primevue/card'
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import SpecialTaskStatusBadge from '../atoms/SpecialTaskStatusBadge.vue'
import type { SpecialTask } from '@/types/qualifications'

interface Props {
  specialTask: SpecialTask
  showActions?: boolean
}

withDefaults(defineProps<Props>(), {
  showActions: true
})

const emit = defineEmits<{
  view: [id: number]
  edit: [id: number]
  delete: [id: number]
  end: [id: number]
}>()

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}
</script>

<style scoped>
.special-task-card {
  height: 100%;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.card-header-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.person-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.person-name {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-color);
}

.task-chip {
  font-size: 0.875rem;
}

.card-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.875rem;
}

.detail-label {
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.detail-value {
  color: var(--text-color);
  font-weight: 500;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-border);
}

@media (max-width: 768px) {
  .card-actions {
    flex-direction: column;
  }

  .card-actions :deep(.p-button) {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
