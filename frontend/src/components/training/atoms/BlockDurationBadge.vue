<template>
  <Tag :value="label" :severity="severity" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'

const props = defineProps<{ minutes: number }>()

const label = computed(() => {
  const m = props.minutes
  if (m < 60) return `${m} Min`
  const h = Math.floor(m / 60)
  const rest = m % 60
  return rest > 0 ? `${h}h ${rest}m` : `${h}h`
})

const severity = computed(() => {
  if (props.minutes <= 15) return 'info'
  if (props.minutes <= 45) return 'success'
  if (props.minutes <= 90) return 'warn'
  return 'danger'
})
</script>
