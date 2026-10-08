<template>
  <span class="category-badge" :style="badgeStyle">
    <span class="category-swatch" aria-hidden="true"></span>
    <i v-if="category.icon" :class="['pi', category.icon]" aria-hidden="true"></i>
    {{ category.name }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { safeBlockColor } from '../utils/blockColor'
import type { LibraryBlockCategory } from '@/types/training'

const props = defineProps<{ category: LibraryBlockCategory }>()

// The category colour marks the swatch only; the label keeps the theme text colour
// so light colours such as yellow stay readable.
const badgeStyle = computed(() => {
  const color = safeBlockColor(props.category.color)
  return color ? { '--category-color': color } : {}
})
</script>

<style scoped>
.category-badge {
  --category-color: var(--jf-color-text-muted);
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  padding: 0.125rem var(--jf-space-1);
  border-radius: 9999px;
  border: 1px solid color-mix(in srgb, var(--category-color) 45%, var(--jf-color-card));
  background: color-mix(in srgb, var(--category-color) 10%, var(--jf-color-card));
  color: var(--jf-color-text);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-medium);
  white-space: nowrap;
}
.category-swatch {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 9999px;
  background: var(--category-color);
  flex: none;
}
</style>
