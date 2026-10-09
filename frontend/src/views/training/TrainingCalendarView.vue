<template>
  <div class="training-calendar-view">
    <OverviewHeader title="Ausbildungsplanung" subtitle="Trainingsübungen planen und verwalten" />
    <TrainingCalendar />
  </div>
</template>

<script setup lang="ts">
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import TrainingCalendar from '@/components/training/organisms/TrainingCalendar.vue'
</script>

<style scoped>
/* The app layout already pads and caps the content width; the calendar uses all of it. */
.training-calendar-view {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.training-calendar-view :deep(.overview-header) {
  margin-bottom: var(--jf-space-2);
  padding-bottom: 0;
}
</style>
