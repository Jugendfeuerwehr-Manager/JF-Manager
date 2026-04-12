<template>
  <div class="special-tasks-mobile-list">
    <ResponsiveList
      :items="items"
      :loading="loading"
      :rows="rows"
      :paginator="totalRecords > rows"
      :total-records="totalRecords"
      :lazy="true"
      item-key="id"
      @page="handlePage"
    >
      <template #item="{ item: task }">
        <article class="task-mobile-row">
          <div class="task-mobile-row__header">
            <div>
              <p class="task-mobile-row__person">{{ task.person_name }}</p>
              <p class="task-mobile-row__task">{{ task.task_name }}</p>
            </div>
            <Tag :value="getStatusLabel(task)" :severity="getStatusSeverity(task)" />
          </div>

          <div class="task-mobile-row__meta">
            <div>
              <span>Start</span>
              <strong>{{ formatDate(task.start_date) }}</strong>
            </div>
            <div>
              <span>Ende</span>
              <strong>{{ formatEnd(task) }}</strong>
            </div>
          </div>

          <div v-if="task.note" class="task-mobile-row__notes">
            {{ task.note }}
          </div>

          <div class="task-mobile-row__actions">
            <Button
              icon="pi pi-eye"
              label="Ansehen"
              size="small"
              outlined
              @click="emit('view', task.id)"
            />
            <Button
              icon="pi pi-pencil"
              label="Bearbeiten"
              size="small"
              outlined
              severity="secondary"
              @click="emit('edit', task.id)"
            />
            <Button
              v-if="task.is_active"
              icon="pi pi-check"
              label="Beenden"
              size="small"
              outlined
              severity="success"
              @click="emit('end', task.id)"
            />
            <Button
              icon="pi pi-trash"
              size="small"
              outlined
              severity="danger"
              @click="emit('delete', task.id)"
            />
          </div>
        </article>
      </template>

      <template #empty>
        <div class="mobile-list-empty">
          <i class="pi pi-briefcase"></i>
          <p>Keine Sonderaufgaben gefunden</p>
        </div>
      </template>
    </ResponsiveList>
  </div>
</template>

<script setup lang="ts">
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import type { SpecialTask } from '@/types/qualifications'
import ResponsiveList from '@/components/common/ResponsiveList.vue'
import type { DataViewPageEvent } from 'primevue/dataview'

interface Props {
  items: SpecialTask[]
  loading?: boolean
  rows?: number
  totalRecords?: number
}

withDefaults(defineProps<Props>(), {
  loading: false,
  rows: 10,
  totalRecords: 0
})

const emit = defineEmits<{
  (e: 'view', id: number): void
  (e: 'edit', id: number): void
  (e: 'end', id: number): void
  (e: 'delete', id: number): void
  (e: 'page-change', page: number, rows: number): void
}>()

const handlePage = (event: DataViewPageEvent) => {
  const page = Math.floor(event.first / event.rows) + 1
  emit('page-change', page, event.rows)
}

function formatDate(value: string | null): string {
  if (!value) return '–'
  return new Date(value).toLocaleDateString('de-DE')
}

function formatEnd(task: SpecialTask): string {
  if (!task.end_date && task.is_active) return 'Noch aktiv'
  return task.end_date ? formatDate(task.end_date) : '–'
}

function getStatusLabel(task: SpecialTask): string {
  return task.is_active ? 'Aktiv' : 'Beendet'
}

function getStatusSeverity(task: SpecialTask): 'success' | 'warning' {
  return task.is_active ? 'success' : 'warning'
}
</script>

<style scoped>
.special-tasks-mobile-list {
  width: 100%;
}

.task-mobile-row {
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  padding: 0.9rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  background: var(--surface-card);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.task-mobile-row__header {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}

.task-mobile-row__person {
  margin: 0;
  font-weight: 600;
  font-size: 1rem;
}

.task-mobile-row__task {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.task-mobile-row__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  font-size: 0.85rem;
}

.task-mobile-row__meta span {
  display: block;
  color: var(--text-color-secondary);
  font-size: 0.75rem;
  margin-bottom: 0.15rem;
}

.task-mobile-row__meta strong {
  font-size: 0.95rem;
}

.task-mobile-row__notes {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.task-mobile-row__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

@media (max-width: 480px) {
  .task-mobile-row__actions {
    flex-direction: column;
  }
}
</style>
