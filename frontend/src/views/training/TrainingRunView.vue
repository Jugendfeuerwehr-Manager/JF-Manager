<template>
  <TrainingRun :session-id="sessionId" />
</template>

<script setup lang="ts">
import TrainingRun from '@/components/training/organisms/TrainingRun.vue'

defineProps<{ sessionId: number }>()
</script>
