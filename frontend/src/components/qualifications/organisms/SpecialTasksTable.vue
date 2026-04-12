<script setup lang="ts">
import { computed } from 'vue'
import type { SpecialTask } from '@/types/qualifications'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

interface Props {
  tasks: SpecialTask[]
  loading?: boolean
  showActions?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  tasks: () => [],
  loading: false,
  showActions: true
})

const emit = defineEmits<{
  view: [id: number]
  edit: [id: number]
  end: [id: number]
  delete: [id: number]
}>()

const hasTasks = computed(() => props.tasks.length > 0)

function formatDate(value: string | null): string {
  if (!value) return '–'
  return new Date(value).toLocaleDateString('de-DE')
}

function getStatusSeverity(task: SpecialTask): 'success' | 'warning' {
  return task.is_active ? 'success' : 'warning'
}

function getStatusLabel(task: SpecialTask): string {
  return task.is_active ? 'Aktiv' : 'Beendet'
}

function getRowClass(task: SpecialTask) {
  return task.is_active ? '' : 'row-ended'
}
</script>

<template>
  <div class="tasks-table">
    <DataTable
      v-if="hasTasks"
      :value="tasks"
      :loading="loading"
      :rowClass="getRowClass"
      responsiveLayout="stack"
      breakpoint="768px"
      stripedRows
    >
      <Column field="task_name" header="Aufgabe" style="min-width: 200px">
        <template #body="{ data }">
          <div class="cell-primary">
            <strong>{{ data.task_name }}</strong>
            <small class="cell-secondary">{{ data.task_details?.description }}</small>
          </div>
        </template>
      </Column>

      <Column field="person_name" header="Zugeordnet an" style="min-width: 200px">
        <template #body="{ data }">
          <div class="cell-primary">
            {{ data.person_name }}
          </div>
          <small v-if="data.user_name" class="cell-secondary">Benutzer: {{ data.user_name }}</small>
        </template>
      </Column>

      <Column field="start_date" header="Start" style="min-width: 140px">
        <template #body="{ data }">
          {{ formatDate(data.start_date) }}
        </template>
      </Column>

      <Column field="end_date" header="Ende" style="min-width: 140px">
        <template #body="{ data }">
          {{ data.end_date ? formatDate(data.end_date) : 'Noch aktiv' }}
        </template>
      </Column>

      <Column header="Status" style="min-width: 120px">
        <template #body="{ data }">
          <Tag :value="getStatusLabel(data)" :severity="getStatusSeverity(data)" />
        </template>
      </Column>

      <Column v-if="showActions" header="Aktionen" style="min-width: 180px">
        <template #body="{ data }">
          <div class="action-buttons">
            <Button
              icon="pi pi-eye"
              text
              rounded
              severity="secondary"
              size="small"
              @click="emit('view', data.id)"
              v-tooltip.top="'Details'"
            />
            <Button
              icon="pi pi-pencil"
              text
              rounded
              severity="info"
              size="small"
              @click="emit('edit', data.id)"
              v-tooltip.top="'Bearbeiten'"
            />
            <Button
              v-if="data.is_active"
              icon="pi pi-check"
              text
              rounded
              severity="success"
              size="small"
              @click="emit('end', data.id)"
              v-tooltip.top="'Beenden'"
            />
            <Button
              icon="pi pi-trash"
              text
              rounded
              severity="danger"
              size="small"
              @click="emit('delete', data.id)"
              v-tooltip.top="'Löschen'"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <Message v-else severity="info" :closable="false" class="empty-message">
      Keine Sonderaufgaben vorhanden.
    </Message>
  </div>
</template>

<style scoped>
.tasks-table {
  width: 100%;
}

.cell-primary {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.cell-secondary {
  color: var(--text-color-secondary);
}

.action-buttons {
  display: flex;
  gap: 0.35rem;
}

.row-ended {
  background-color: rgba(148, 163, 184, 0.15);
}

.empty-message {
  display: flex;
  justify-content: center;
  margin: 1rem 0;
}
</style>
