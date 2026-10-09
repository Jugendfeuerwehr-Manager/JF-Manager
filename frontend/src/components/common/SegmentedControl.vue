<template>
  <div class="segmented" role="group" :aria-label="label">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      :aria-pressed="option.value === modelValue"
      @click="emit('update:modelValue', option.value)"
    >
      <span>{{ option.label }}</span>
      <template v-if="option.count !== undefined && option.count !== null">
        <span class="segmented__count" :aria-hidden="option.countLabel ? 'true' : undefined">{{ option.count }}</span>
        <span v-if="option.countLabel" class="sr-only">, {{ option.countLabel }}</span>
      </template>
    </button>
  </div>
</template>

<script setup lang="ts" generic="T extends string | number">
/** One shared look for view and period switches (DES-01/UX consistency contract). */
export interface SegmentedOption<V> {
  value: V
  label: string
  /** Optional number shown next to the label, e.g. how many entries a view holds. */
  count?: number | null
  /** Spoken instead of the bare number, e.g. "2 offene Anträge" (the number alone gives no context). */
  countLabel?: string
}

defineProps<{ modelValue: T; options: SegmentedOption<T>[]; label: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: T] }>()
</script>

<style scoped>
.segmented {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-border);
  flex-wrap: wrap;
  max-width: 100%;
}

.segmented button {
  flex: 1 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--jf-space-1);
  min-height: 40px;
  padding: 0 var(--jf-space-1-5);
  border: 0;
  border-radius: var(--jf-radius-sm);
  background: transparent;
  color: var(--jf-color-text-muted);
  font: inherit;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  white-space: nowrap;
  cursor: pointer;
}

.segmented button:hover { color: var(--jf-color-text); }
.segmented button:focus-visible { outline: var(--jf-focus-ring); outline-offset: 1px; }

.segmented button[aria-pressed='true'] {
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  box-shadow: var(--jf-shadow-sm);
}

.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

.segmented__count {
  min-width: 1.5rem;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--jf-color-ground);
  font-size: var(--jf-text-xs);
  line-height: 1.5rem;
}
</style>
