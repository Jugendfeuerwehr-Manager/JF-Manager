<template>
  <div class="qual-mobile-list">
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
      <template #item="{ item: qualification }">
        <article class="qual-mobile-row">
          <div class="qual-mobile-row__header">
            <div>
              <p class="qual-mobile-row__person">{{ qualification.person_name }}</p>
              <p class="qual-mobile-row__type">{{ qualification.type_name }}</p>
            </div>
            <Tag :value="getStatusLabel(qualification)" :severity="getStatusSeverity(qualification)" />
          </div>

          <div class="qual-mobile-row__meta">
            <div>
              <span>Erworben</span>
              <strong>{{ formatDate(qualification.date_acquired) }}</strong>
            </div>
            <div>
              <span>Gültig bis</span>
              <strong>{{ formatExpiry(qualification) }}</strong>
            </div>
          </div>

          <div class="qual-mobile-row__notes" v-if="qualification.issued_by || qualification.note">
            <span v-if="qualification.issued_by">Ausgestellt von {{ qualification.issued_by }}</span>
            <span v-if="qualification.note">{{ qualification.note }}</span>
          </div>

          <div class="qual-mobile-row__actions">
            <Button
              icon="pi pi-eye"
              label="Ansehen"
              size="small"
              outlined
              @click="emit('view', qualification.id)"
            />
            <Button
              icon="pi pi-pencil"
              label="Bearbeiten"
              size="small"
              outlined
              severity="secondary"
              @click="emit('edit', qualification.id)"
            />
            <Button
              icon="pi pi-trash"
              size="small"
              outlined
              severity="danger"
              @click="emit('delete', qualification.id)"
            />
          </div>
        </article>
      </template>

      <template #empty>
        <div class="mobile-list-empty">
          <i class="pi pi-certificate"></i>
          <p>Keine Qualifikationen gefunden</p>
        </div>
      </template>
    </ResponsiveList>
  </div>
</template>

<script setup lang="ts">
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import type { Qualification } from '@/types/qualifications'
import ResponsiveList from '@/components/common/ResponsiveList.vue'
import type { DataViewPageEvent } from 'primevue/dataview'

interface Props {
  items: Qualification[]
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
  (e: 'delete', id: number): void
  (e: 'page-change', page: number, rows: number): void
}>()

const handlePage = (event: DataViewPageEvent) => {
  const page = Math.floor(event.first / event.rows) + 1
  emit('page-change', page, event.rows)
}

function formatDate(value: string | null): string {
  if (!value) return '-'
  return new Date(value).toLocaleDateString('de-DE')
}

function formatExpiry(qualification: Qualification): string {
  if (!qualification.date_expires) return 'Unbegrenzt'
  const date = formatDate(qualification.date_expires)
  if (qualification.is_expired) return `${date} (abgelaufen)`
  return date
}

function getStatusLabel(qualification: Qualification): string {
  if (qualification.is_expired) return 'Abgelaufen'
  if (qualification.expires_soon) return 'Läuft bald ab'
  return 'Gültig'
}

function getStatusSeverity(qualification: Qualification): 'success' | 'warning' | 'danger' {
  if (qualification.is_expired) return 'danger'
  if (qualification.expires_soon) return 'warning'
  return 'success'
}
</script>

<style scoped>
.qual-mobile-list {
  width: 100%;
}

.qual-mobile-row {
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  padding: 0.9rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  background: var(--surface-card);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.qual-mobile-row__header {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}

.qual-mobile-row__person {
  margin: 0;
  font-weight: 600;
  font-size: 1rem;
}

.qual-mobile-row__type {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.qual-mobile-row__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  font-size: 0.85rem;
}

.qual-mobile-row__meta span {
  display: block;
  color: var(--text-color-secondary);
  font-size: 0.75rem;
  margin-bottom: 0.15rem;
}

.qual-mobile-row__meta strong {
  font-size: 0.95rem;
}

.qual-mobile-row__notes {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.qual-mobile-row__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

@media (max-width: 480px) {
  .qual-mobile-row__actions {
    flex-direction: column;
  }
}
</style>
