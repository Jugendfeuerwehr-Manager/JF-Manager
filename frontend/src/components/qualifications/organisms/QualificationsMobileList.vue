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
        <button
          type="button"
          class="qual-mobile-row"
          :aria-label="`${qualification.type_name} von ${qualification.person_name} öffnen`"
          @click="emit('view', qualification.id)"
        >
          <span class="qual-mobile-row__main">
            <span class="qual-mobile-row__person">{{ qualification.person_name }}</span>
            <span class="qual-mobile-row__type">{{ qualification.type_name }}</span>
            <span class="qual-mobile-row__badges">
              <StatusBadge v-bind="qualificationStatus(qualification)" />
              <StatusBadge v-if="qualification.has_evidence === false" label="Nachweis fehlt" severity="neutral" icon="pi pi-file" />
            </span>
          </span>
          <span class="qual-mobile-row__date">
            <span>Gültig bis</span>
            <strong>{{ qualification.date_expires ? formatDate(qualification.date_expires) : 'unbefristet' }}</strong>
          </span>
          <i class="pi pi-chevron-right qual-mobile-row__chevron" aria-hidden="true"></i>
        </button>
      </template>

      <template #empty>
        <StateView kind="empty" title="Keine Qualifikationen gefunden" message="Passe Suche oder Filter an oder lege einen neuen Eintrag an." />
      </template>
    </ResponsiveList>
  </div>
</template>

<script setup lang="ts">
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { Qualification } from '@/types/qualifications'
import ResponsiveList from '@/components/common/ResponsiveList.vue'
import type { DataViewPageEvent } from 'primevue/dataview'
import { formatDate, qualificationStatus } from '../utils/qualificationStatus'

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
  (e: 'page-change', page: number, rows: number): void
}>()

const handlePage = (event: DataViewPageEvent) => {
  const page = Math.floor(event.first / event.rows) + 1
  emit('page-change', page, event.rows)
}

</script>

<style scoped>
.qual-mobile-list { width: 100%; }

/* Tapping a card opens the detail view; editing and deleting live there (as in the member list). */
.qual-mobile-row {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  width: 100%;
  min-height: var(--jf-touch-target);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.qual-mobile-row:hover { background: var(--p-content-hover-background); }
.qual-mobile-row:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
.qual-mobile-row__main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.qual-mobile-row__person { font-weight: var(--jf-weight-semibold); }
.qual-mobile-row__type { font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.qual-mobile-row__badges { display: flex; flex-wrap: wrap; gap: var(--jf-space-0-5); margin-top: var(--jf-space-0-5); }
.qual-mobile-row__date { display: flex; flex-direction: column; align-items: flex-end; font-size: var(--jf-text-sm); white-space: nowrap; }
.qual-mobile-row__date span { font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }
.qual-mobile-row__chevron { color: var(--jf-color-text-muted); font-size: var(--jf-text-xs); }
</style>
