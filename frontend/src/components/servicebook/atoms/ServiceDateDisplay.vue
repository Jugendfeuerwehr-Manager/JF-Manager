<template>
  <div class="service-date-display">
    <div class="date-icon">
      <i class="pi pi-calendar"></i>
    </div>
    <div class="date-content">
      <div class="date-primary">{{ formattedDate }}</div>
      <div class="date-secondary">{{ formattedTime }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { format, parseISO } from 'date-fns'
import { de } from 'date-fns/locale'

interface Props {
  start: string
  end: string
  showEndDate?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showEndDate: false
})

const formattedDate = computed(() => {
  try {
    const startDate = parseISO(props.start)
    return format(startDate, 'd. MMM yyyy', { locale: de })
  } catch {
    return props.start
  }
})

const formattedTime = computed(() => {
  try {
    const startDate = parseISO(props.start)
    const endDate = parseISO(props.end)
    const startTime = format(startDate, 'HH:mm')
    const endTime = format(endDate, 'HH:mm')
    return `${startTime} - ${endTime}`
  } catch {
    return `${props.start} - ${props.end}`
  }
})
</script>

<style scoped>
.service-date-display {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.date-icon {
  color: var(--primary-color);
  font-size: 1.25rem;
}

.date-content {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.date-primary {
  font-weight: 500;
  color: var(--text-color);
  font-size: 0.95rem;
}

.date-secondary {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}
</style>
