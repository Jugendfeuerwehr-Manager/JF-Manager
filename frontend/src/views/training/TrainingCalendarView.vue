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
/*
 * The route is marked wide (no 1600 px cap, UX-09); the calendar uses the full width
 * and on desktops the remaining screen height below the top bar.
 */
.training-calendar-view {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

@media (min-width: 1024px) {
  /* A definite height lets the month rows share the screen; the list keeps growing. */
  .training-calendar-view:has(.cal-grid) {
    height: calc(100dvh - var(--topbar-height, 64px) - 2 * var(--jf-space-3));
  }
}

.training-calendar-view :deep(.overview-header) {
  margin-bottom: var(--jf-space-2);
  padding-bottom: 0;
}
</style>
