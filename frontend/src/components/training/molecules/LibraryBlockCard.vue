<template>
  <div class="library-block-card" :style="{ borderLeftColor: block.color ?? 'var(--primary-color)' }" @click="emit('click', block)">
    <div class="card-header">
      <span class="card-title">{{ block.title }}</span>
      <slot name="actions" />
    </div>

    <div class="card-meta">
      <LibraryBlockCategoryBadge v-if="categoryObj" :category="categoryObj" />
      <BlockDurationBadge v-if="block.default_duration_minutes" :minutes="block.default_duration_minutes" />
    </div>

    <p v-if="block.description" class="card-description">{{ block.description }}</p>

    <div v-if="block.tags.length" class="card-tags">
      <Tag v-for="tag in block.tags" :key="tag.id" :value="tag.name" severity="secondary" class="mr-1" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'
import LibraryBlockCategoryBadge from '../atoms/LibraryBlockCategoryBadge.vue'
import BlockDurationBadge from '../atoms/BlockDurationBadge.vue'
import type { LibraryBlockList, LibraryBlockCategory } from '@/types/training'

const props = defineProps<{ block: LibraryBlockList }>()
const emit = defineEmits<{ click: [block: LibraryBlockList] }>()

/** Construct a category object from the flat list fields */
const categoryObj = computed<LibraryBlockCategory | null>(() => {
  if (props.block.category === null) return null
  return {
    id: props.block.category,
    name: props.block.category_name ?? '',
    color: props.block.category_color ?? '',
    icon: '',
  }
})
</script>

<style scoped>
.library-block-card {
  border: 1px solid var(--surface-border);
  border-left: 4px solid var(--primary-color);
  border-radius: var(--border-radius);
  padding: 0.875rem 1rem;
  background: var(--surface-card);
  cursor: pointer;
  transition: box-shadow 0.15s;
}
.library-block-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.card-title {
  font-weight: 600;
  font-size: 0.95rem;
}
.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.card-description {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  margin: 0 0 0.5rem;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}
</style>
