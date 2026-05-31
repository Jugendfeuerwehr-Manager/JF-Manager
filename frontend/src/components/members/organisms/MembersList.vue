<template>
  <!-- Desktop table -->
  <MembersTable
    v-if="!isMobile"
    :members="members"
    :loading="loading"
    :first="first"
    :rows="rows"
    :total-records="totalRecords"
    :departments="departments"
    :show-departments="showDepartments"
    @page="emit('page', $event)"
    @sort="emit('sort', $event)"
    @view="emit('view', $event)"
    @edit="emit('edit', $event)"
    @delete="emit('delete', $event)"
  />

  <!-- Mobile cards -->
  <MembersMobileList
    v-else
    :members="members"
    :loading="loading"
    :rows="rows"
    :total-records="totalRecords"
    @page="emit('page', $event)"
    @view="emit('view', $event)"
    @edit="emit('edit', $event)"
    @delete="emit('delete', $event)"
  />
</template>

<script setup lang="ts">
import { useMobile } from '@/composables/useMobile'
import MembersTable from '@/components/members/organisms/MembersTable.vue'
import MembersMobileList from '@/components/members/organisms/MembersMobileList.vue'
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
  page: [event: DataTablePageEvent | { first: number; rows: number }]
  sort: [event: DataTableSortEvent]
  view: [member: Member]
  edit: [member: Member]
  delete: [member: Member]
}>()

const { isMobile } = useMobile()
</script>
