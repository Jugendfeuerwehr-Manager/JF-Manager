<template>
  <span class="department-tag" :class="{ 'department-tag--all': departmentId == null }">
    <i v-if="departmentId == null" class="pi pi-globe" aria-hidden="true"></i>
    <span v-else class="department-tag__dot" :style="{ backgroundColor: department?.color || undefined }" aria-hidden="true"></span>
    <span class="visually-hidden">Abteilung: </span>{{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDepartmentsStore } from '@/stores/departments'

interface Props {
  /** ``null`` marks a record for the whole organisation. */
  departmentId: number | null | undefined
}

const props = defineProps<Props>()
const departmentsStore = useDepartmentsStore()

const department = computed(() => departmentsStore.departments.find((d) => d.id === props.departmentId) ?? null)
const label = computed(() => (props.departmentId == null ? 'Alle Abteilungen' : department.value?.name ?? 'Abteilung'))
</script>

<style scoped>
.department-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--jf-color-border);
  color: var(--jf-color-text-muted);
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.5;
  white-space: nowrap;
}

.department-tag--all {
  color: var(--jf-color-primary);
  border-color: var(--jf-color-primary);
}

.department-tag i {
  font-size: 0.8em;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.department-tag__dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: var(--jf-color-text-muted);
}
</style>
