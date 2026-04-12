<template>
  <Card class="statistics-card">
    <template #content>
      <div class="stats-content">
        <div class="stats-info">
          <h6 class="stats-title">{{ title }}</h6>
          <h3 class="stats-value" :class="`text-${severity}`">{{ value }}</h3>
        </div>
        <div class="stats-icon" :class="`text-${severity}`">
          <i :class="`pi ${icon} text-4xl`"></i>
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import Card from 'primevue/card'

interface Props {
  title: string
  value: number | string
  icon: string
  severity?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
}

withDefaults(defineProps<Props>(), {
  severity: 'primary'
})
</script>

<style scoped>
.statistics-card {
  height: 100%;
}

.stats-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
}

.stats-info {
  flex: 1;
}

.stats-title {
  color: var(--text-color-secondary);
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  font-weight: 500;
}

.stats-value {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
}

.stats-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.6;
}

.text-primary {
  color: var(--primary-color);
}

.text-success {
  color: var(--green-500);
}

.text-warning {
  color: var(--orange-500);
}

.text-danger {
  color: var(--red-500);
}

.text-info {
  color: var(--blue-500);
}
</style>
