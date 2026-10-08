<template>
  <div class="attendance-button-group" role="group" :aria-label="personName ? `Anwesenheit von ${personName}` : 'Anwesenheit'">
    <button
      v-for="state in states"
      :key="state.value"
      type="button"
      class="attendance-option"
      :class="[`attendance-option--${state.value}`, { 'attendance-option--active': isActive(state.value) }]"
      :aria-pressed="isActive(state.value)"
      :disabled="disabled || loading"
      @click="handleClick(state.value)"
    >
      <i :class="state.icon" aria-hidden="true"></i>
      <span>{{ state.title }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { AttendanceState } from '@/types/servicebook'

interface Props {
  currentState: AttendanceState | null
  /** Names the group for screen readers, e.g. "Anwesenheit von Lena Weber". */
  personName?: string
  loading?: boolean
  disabled?: boolean
}

interface Emits {
  (e: 'select', state: AttendanceState): void
}

const props = withDefaults(defineProps<Props>(), {
  personName: '',
  loading: false,
  disabled: false,
})

const emit = defineEmits<Emits>()

const states = [
  { value: AttendanceState.PRESENT, title: 'Anwesend', icon: 'pi pi-check' },
  { value: AttendanceState.EXCUSED, title: 'Entschuldigt', icon: 'pi pi-clock' },
  { value: AttendanceState.ABSENT, title: 'Fehlt', icon: 'pi pi-times' },
]

const isActive = (state: AttendanceState) => props.currentState === state

const handleClick = (state: AttendanceState) => {
  if (props.loading || props.disabled) return
  emit('select', state)
}
</script>

<style scoped>
.attendance-button-group {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--jf-space-1);
}

.attendance-option {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: var(--jf-touch-target);
  padding: 0 var(--jf-space-1);
  border: 1px solid var(--p-surface-300);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  cursor: pointer;
  transition: background var(--jf-duration), border-color var(--jf-duration);
}

.attendance-option:disabled {
  cursor: progress;
  opacity: 0.7;
}

.attendance-option i {
  font-size: 0.8rem;
}

.attendance-option--A.attendance-option--active { border-color: var(--p-green-700); background: var(--p-green-700); color: #fff; }
.attendance-option--E.attendance-option--active { border-color: var(--p-amber-500); background: var(--p-amber-100); color: var(--p-amber-900); }
.attendance-option--F.attendance-option--active { border-color: var(--p-red-700); background: var(--p-red-100); color: var(--p-red-800); }

.app-dark .attendance-option--A.attendance-option--active { border-color: var(--p-green-400); background: color-mix(in srgb, var(--p-green-400), transparent 70%); color: var(--p-green-100); }
.app-dark .attendance-option--E.attendance-option--active { border-color: var(--p-amber-400); background: color-mix(in srgb, var(--p-amber-400), transparent 75%); color: var(--p-amber-100); }
.app-dark .attendance-option--F.attendance-option--active { border-color: var(--p-red-400); background: color-mix(in srgb, var(--p-red-400), transparent 75%); color: var(--p-red-100); }
</style>
