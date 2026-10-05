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
        removable-sort
        @page="emit('page', $event)"
        @sort="emit('sort', $event)"
        @row-click="(e) => emit('view', e.data)"
        class="clickable-rows"
      >
        <Column field="lastname" header="Name" sortable>
          <template #body="{ data }">
            <MemberIdentity :member="data">
              <span v-if="data.age">{{ data.age }} Jahre</span>
              <span v-if="data.has_alert" class="alert-hint" v-tooltip.top="'In den letzten Diensten häufig nicht anwesend'"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i>Teilnahme prüfen</span>
            </MemberIdentity>
          </template>
        </Column>
        <Column header="Gruppe">
          <template #body="{ data }">{{ data.group?.name ?? '–' }}</template>
        </Column>
        <Column field="birthday" header="Geburtstag" sortable>
          <template #body="{ data }">{{ formatDate(data.birthday) }}</template>
        </Column>
        <Column header="Status">
          <template #body="{ data }"><MemberStatusBadge :status="data.status" /></template>
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

        <Column :style="{ width: '7rem' }">
          <template #header><span class="sr-only">Aktionen</span></template>
          <template #body="{ data }">
            <div class="action-buttons">
              <Button icon="pi pi-pencil" text rounded severity="secondary" :aria-label="`${data.full_name} bearbeiten`" v-tooltip.top="'Bearbeiten'" @click.stop="emit('edit', data)" />
              <Button icon="pi pi-trash" text rounded severity="danger" :aria-label="`${data.full_name} löschen`" v-tooltip.top="'Löschen'" @click.stop="emit('delete', data)" />
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
import MemberIdentity from '@/components/members/atoms/MemberIdentity.vue'
import MemberStatusBadge from '@/components/members/atoms/MemberStatusBadge.vue'
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
  overflow: hidden;
}

.table-card :deep(.p-card-body) {
  padding: 0;
}

.table-card :deep(.p-datatable-tbody > tr > td) {
  padding-block: var(--jf-space-1-5);
}

.action-buttons {
  display: flex;
  gap: var(--jf-space-0-5);
  justify-content: flex-end;
}

.dept-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.alert-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--p-amber-800);
  font-weight: var(--jf-weight-semibold);
}

.app-dark .alert-hint {
  color: var(--p-amber-300);
}

.alert-hint i {
  font-size: 0.75rem;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.clickable-rows :deep(tbody tr) {
  cursor: pointer;
  transition: background-color var(--jf-duration);
}

.clickable-rows :deep(tbody tr:hover) {
  background-color: var(--surface-hover) !important;
}
</style>
