<template>
  <Tag 
    :value="label" 
    :severity="severity" 
    :icon="icon"
    
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'
import { AttendanceState, AttendanceStateLabels, AttendanceStateColors } from '@/types/servicebook'

interface Props {
  state: AttendanceState | null
}

const props = defineProps<Props>()

const label = computed(() => {
  if (!props.state) return 'Nicht erfasst'
  return AttendanceStateLabels[props.state]
})

const severity = computed(() => {
  if (!props.state) return 'secondary'
  return AttendanceStateColors[props.state] as 'success' | 'warn' | 'danger' | 'secondary'
})

const icon = computed(() => {
  if (!props.state) return 'pi pi-minus'
  switch (props.state) {
    case AttendanceState.PRESENT:
      return 'pi pi-check'
    case AttendanceState.EXCUSED:
      return 'pi pi-exclamation-triangle'
    case AttendanceState.ABSENT:
      return 'pi pi-times'
    default:
      return 'pi pi-minus'
  }
})
</script>
