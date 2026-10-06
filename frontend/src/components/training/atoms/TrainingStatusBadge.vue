<template>
  <StatusBadge :label="states[status].label" :severity="states[status].severity" />
</template>
<script setup lang="ts">
import StatusBadge, { type StatusSeverity } from '@/components/common/StatusBadge.vue'
import type { TrainingStatus } from '@/types/training'
withDefaults(defineProps<{ status?: TrainingStatus }>(), { status: 'draft' })
const states: Record<TrainingStatus, { label: string; severity: StatusSeverity }> = {
  draft: { label: 'Entwurf', severity: 'neutral' },
  published: { label: 'Veröffentlicht', severity: 'info' },
  completed: { label: 'Abgeschlossen', severity: 'success' },
  cancelled: { label: 'Abgesagt', severity: 'danger' },
}
</script>
