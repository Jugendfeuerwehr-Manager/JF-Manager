<template>
  <Card class="table-card">
    <template #content>
      <DataTable
        :value="members"
        :lazy="true"
        :paginator="true"
        :rows="rows"
        :first="first"
        :total-records="totalRecords"
        :loading="loading"
        :rows-per-page-options="[10, 20, 50]"
        paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
        current-page-report-template="{first} bis {last} von {totalRecords}"
        striped-rows
        removable-sort
        @page="emit('page', $event)"
        @sort="emit('sort', $event)"
        @row-click="(e) => emit('view', e.data)"
        class="clickable-rows"
      >
        <Column :style="{ width: '3rem' }">
          <template #body="{ data }">
            <i
              v-if="data.has_alert"
              class="pi pi-exclamation-triangle alert-icon"
              v-tooltip.top="'Anwesenheitsalarm'"
            />
          </template>
        </Column>

        <Column field="name" header="Vorname" sortable />
        <Column field="lastname" header="Nachname" sortable />

        <Column field="birthday" header="Geburtstag" sortable>
          <template #body="{ data }">
            {{ formatDate(data.birthday) }} ({{ data.age }})
          </template>
        </Column>

        <Column field="status" header="Status">
          <template #body="{ data }">
            <Tag
              v-if="data.status"
              :value="data.status.name"
              :style="{ backgroundColor: data.status.color, color: 'white' }"
            />
          </template>
        </Column>

        <Column
          v-if="showDepartments"
          header="Abteilung"
        >
          <template #body="{ data }">
            <div class="dept-badges">
              <DepartmentBadge
                v-for="deptId in data.department_ids"
                :key="deptId"
                :department="departments.find((d) => d.id === deptId) ?? null"
              />
            </div>
          </template>
        </Column>

        <Column header="Aktionen" :style="{ width: '12rem' }">
          <template #body="{ data }">
            <div class="action-buttons">
              <Button
                icon="pi pi-eye"
                size="small"
                text
                rounded
                title="Ansehen"
                @click.stop="emit('view', data)"
              />
              <Button
                icon="pi pi-pencil"
                size="small"
                text
                rounded
                severity="secondary"
                title="Bearbeiten"
                @click.stop="emit('edit', data)"
              />
              <Button
                icon="pi pi-trash"
                size="small"
                text
                rounded
                severity="danger"
                title="Löschen"
                @click.stop="emit('delete', data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </template>
  </Card>
</template>

<script setup lang="ts">
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import DepartmentBadge from '@/components/departments/atoms/DepartmentBadge.vue'
import type { Member } from '@/types/members'
import type { Department } from '@/types/departments'
import type { DataTableSortEvent, DataTablePageEvent } from 'primevue/datatable'

interface Props {
  members: Member[]
  loading: boolean
  first: number
  rows: number
  totalRecords: number
  departments?: Department[]
  showDepartments?: boolean
}

withDefaults(defineProps<Props>(), {
  departments: () => [],
  showDepartments: false,
})

const emit = defineEmits<{
  page: [event: DataTablePageEvent]
  sort: [event: DataTableSortEvent]
  view: [member: Member]
  edit: [member: Member]
  delete: [member: Member]
}>()

function formatDate(dateString: string | null) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}
</script>

<style scoped>
.table-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

.dept-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.alert-icon {
  color: var(--orange-500);
  font-size: 1rem;
}

.clickable-rows :deep(tbody tr) {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.clickable-rows :deep(tbody tr:hover) {
  background-color: var(--surface-hover) !important;
}
</style>
