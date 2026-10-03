<template>
  <div class="attendance-button-group">
    <Button
      v-for="state in states"
      :key="state.value"
      :label="state.label"
      :aria-label="state.title"
      :aria-pressed="isActive(state.value)"
      :title="state.title"
      :severity="getButtonSeverity(state.value)"
      :outlined="!isActive(state.value)"
      :loading="loading"
      :disabled="disabled"
      size="small"
      @click="handleClick(state.value)"
      class="attendance-btn"
    />
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import { AttendanceState, AttendanceStateColors } from '@/types/servicebook'

interface Props {
  currentState: AttendanceState | null
  loading?: boolean
  disabled?: boolean
}

interface Emits {
  (e: 'select', state: AttendanceState): void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  disabled: false,
})

const emit = defineEmits<Emits>()

const states = [
  { value: AttendanceState.PRESENT, label: 'A', title: 'Anwesend' },
  { value: AttendanceState.EXCUSED, label: 'E', title: 'Entschuldigt' },
  { value: AttendanceState.ABSENT, label: 'F', title: 'Fehlend' },
]

const isActive = (state: AttendanceState) => {
  return props.currentState === state
}

const getButtonSeverity = (state: AttendanceState): 'success' | 'warn' | 'danger' => {
  return AttendanceStateColors[state] as 'success' | 'warn' | 'danger'
}

const handleClick = (state: AttendanceState) => {
  if (props.loading || props.disabled) return
  emit('select', state)
}
</script>

<style scoped>
.attendance-button-group {
  display: flex;
  gap: 0.25rem;
}

.attendance-btn {
  min-width: 2.75rem;
  min-height: 2.75rem;
  font-weight: 600;
}
</style>
