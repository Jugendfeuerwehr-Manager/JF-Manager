<template>
  <span class="stock-badge" :class="`stock-badge--${level}`" :title="title">
    <i v-if="level !== 'ok'" :class="level === 'empty' ? 'pi pi-times-circle' : 'pi pi-exclamation-triangle'" aria-hidden="true"></i>
    {{ quantity }}<span class="visually-hidden"> – {{ title }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  quantity: number
  lowThreshold?: number
}

const props = withDefaults(defineProps<Props>(), {
  lowThreshold: 5
})

/** Only empty and low stock are highlighted, so problems stand out from normal stock. */
const level = computed(() => {
  if (props.quantity === 0) return 'empty'
  if (props.quantity <= props.lowThreshold) return 'low'
  return 'ok'
})

const title = computed(() => ({ empty: 'nicht vorrätig', low: 'niedriger Bestand', ok: 'ausreichend' })[level.value])
</script>

<style scoped>
.stock-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 2rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-hover);
  color: var(--jf-color-text);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  font-variant-numeric: tabular-nums;
}

.stock-badge i {
  font-size: 0.75rem;
}

.stock-badge--low { background: var(--p-amber-100); color: var(--p-amber-900); }
.stock-badge--empty { background: var(--p-red-100); color: var(--p-red-800); }
.app-dark .stock-badge--low { background: color-mix(in srgb, var(--p-amber-400), transparent 80%); color: var(--p-amber-200); }
.app-dark .stock-badge--empty { background: color-mix(in srgb, var(--p-red-400), transparent 80%); color: var(--p-red-200); }

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
