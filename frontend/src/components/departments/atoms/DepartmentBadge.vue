<template>
  <Tag
    v-if="department"
    :value="department.code"
    :title="department.name"
    severity="secondary"
    class="dept-badge"
  />
</template>

<script setup lang="ts">
import Tag from 'primevue/tag'
import type { DepartmentMini } from '@/types/departments'

interface Props {
  department: DepartmentMini | null | undefined
}

defineProps<Props>()
</script>

<style scoped>
.dept-badge {
  font-size: 0.7rem;
  padding: 0.1rem 0.4rem;
  letter-spacing: 0.03em;
  font-weight: 600;
  cursor: default;
}
</style>
