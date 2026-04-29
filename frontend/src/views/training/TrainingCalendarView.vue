<template>
  <div class="page-container">
    <div class="page-header">
      <h1>Ausbildungsplanung</h1>
      <p class="text-color-secondary">Trainingsübungen planen und verwalten</p>
    </div>
    <TrainingCalendar />
  </div>
</template>

<script setup lang="ts">
import TrainingCalendar from '@/components/training/organisms/TrainingCalendar.vue'
</script>

<style scoped>
.page-container { padding: 1.5rem; max-width: 1400px; margin: 0 auto; }
.page-header { margin-bottom: 1.5rem; }
.page-header h1 { margin: 0 0 0.25rem; }
</style>
