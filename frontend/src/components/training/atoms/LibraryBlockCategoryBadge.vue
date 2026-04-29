<template>
  <span class="category-badge" :style="badgeStyle">
    <i v-if="category.icon" :class="['pi', category.icon, 'mr-1']"></i>
    {{ category.name }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LibraryBlockCategory } from '@/types/training'

const props = defineProps<{ category: LibraryBlockCategory }>()

const badgeStyle = computed(() => ({
  backgroundColor: props.category.color ? `${props.category.color}22` : 'var(--surface-100)',
  color: props.category.color ?? 'var(--text-color-secondary)',
  border: `1px solid ${props.category.color ?? 'var(--surface-border)'}`,
}))
</script>

<style scoped>
.category-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
}
</style>
