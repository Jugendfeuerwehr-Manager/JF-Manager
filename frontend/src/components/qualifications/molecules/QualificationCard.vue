<template>
  <Card class="qualification-card">
    <template #content>
      <div class="card-body">
        <div class="card-header-section">
          <div class="person-info">
            <h6 class="person-name">{{ qualification.person_name }}</h6>
            <QualificationTypeBadge :type-name="qualification.type_name" />
          </div>
          <QualificationStatusBadge
            :is-expired="qualification.is_expired"
            :expires-soon="qualification.expires_soon"
          />
        </div>

        <div class="card-details">
          <div class="detail-row">
            <span class="detail-label">
              <i class="pi pi-calendar"></i>
              Erworben:
            </span>
            <span class="detail-value">{{ formatDate(qualification.date_acquired) }}</span>
          </div>

          <div v-if="qualification.date_expires" class="detail-row">
            <span class="detail-label">
              <i class="pi pi-clock"></i>
              Läuft ab:
            </span>
            <span class="detail-value">{{ formatDate(qualification.date_expires) }}</span>
          </div>

          <div v-if="qualification.issued_by" class="detail-row">
            <span class="detail-label">
              <i class="pi pi-building"></i>
              Ausgestellt:
            </span>
            <span class="detail-value">{{ qualification.issued_by }}</span>
          </div>
        </div>

        <div v-if="showActions" class="card-actions">
          <Button
            icon="pi pi-eye"
            label="Details"
            size="small"
            text
            @click="emit('view', qualification.id)"
          />
          <Button
            icon="pi pi-pencil"
            label="Bearbeiten"
            size="small"
            text
            @click="emit('edit', qualification.id)"
          />
          <Button
            icon="pi pi-trash"
            label="Löschen"
            size="small"
            text
            severity="danger"
            @click="emit('delete', qualification.id)"
          />
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import Card from 'primevue/card'
import Button from 'primevue/button'
import QualificationStatusBadge from '../atoms/QualificationStatusBadge.vue'
import QualificationTypeBadge from '../atoms/QualificationTypeBadge.vue'
import type { Qualification } from '@/types/qualifications'

interface Props {
  qualification: Qualification
  showActions?: boolean
}

withDefaults(defineProps<Props>(), {
  showActions: true
})

const emit = defineEmits<{
  view: [id: number]
  edit: [id: number]
  delete: [id: number]
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
.qualification-card {
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
