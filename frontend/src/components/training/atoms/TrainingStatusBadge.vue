<template>
  <StatusBadge :label="meta.label" :severity="meta.severity" :icon="meta.icon" />
</template>
<script setup lang="ts">
import { computed } from 'vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import type { TrainingStatus } from '@/types/training'
import { trainingStatusMeta } from '../utils/trainingStatus'

const props = withDefaults(defineProps<{ status?: TrainingStatus }>(), { status: 'draft' })
const meta = computed(() => trainingStatusMeta(props.status))
</script>
