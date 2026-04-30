<template>
  <div class="library-picker">
    <div class="picker-header">
      <h3 class="picker-title">Bibliothek</h3>
      <div class="picker-header-actions">
        <a href="/training/library" target="_blank" class="manage-link" title="Bibliothek verwalten">
          <i class="pi pi-external-link" />
        </a>
        <Button icon="pi pi-times" text size="small" @click="emit('close')" />
      </div>
    </div>

    <InputText v-model="search" placeholder="Suchen…" class="w-full mb-2" @update:model-value="debouncedFetch" />

    <Select
      v-model="filterCategory"
      :options="[{ id: null, name: 'Alle Kategorien' }, ...categories]"
      option-label="name"
      option-value="id"
      class="w-full mb-2"
      @change="fetchBlocks"
    />

    <MultiSelect
      v-model="filterTags"
      :options="tags"
      option-label="name"
      option-value="id"
      placeholder="Tags filtern…"
      class="w-full mb-3"
      :max-selected-labels="2"
      @change="fetchBlocks"
    />

    <div v-if="loading" class="loading"><ProgressSpinner style="width:32px;height:32px" /></div>

    <div v-else class="picker-list">
      <div
        v-for="block in blocks"
        :key="block.id"
        class="picker-item"
        draggable="true"
        @dragstart="onDragStart($event, block)"
        @click="emit('pick', block)"
      >
        <div class="picker-item-header">
          <span class="picker-item-title">{{ block.title }}</span>
          <BlockDurationBadge v-if="block.default_duration_minutes" :minutes="block.default_duration_minutes" />
        </div>
        <div class="picker-item-meta">
          <LibraryBlockCategoryBadge
            v-if="block.category !== null"
            :category="{ id: block.category!, name: block.category_name ?? '', color: block.category_color ?? '', icon: '' }"
          />
          <span v-if="block.last_used_date" class="picker-last-used">
            Zuletzt: {{ formatLastUsed(block.last_used_date) }}
          </span>
          <span v-else class="picker-last-used never">Noch nicht verwendet</span>
        </div>
      </div>

      <p v-if="!blocks.length" class="empty-hint">Keine Bausteine gefunden.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import BlockDurationBadge from '../atoms/BlockDurationBadge.vue'
import LibraryBlockCategoryBadge from '../atoms/LibraryBlockCategoryBadge.vue'
import { useLibraryStore } from '@/stores/library'
import type { LibraryBlockList } from '@/types/training'

const emit = defineEmits<{
  pick: [block: LibraryBlockList]
  close: []
}>()

const libraryStore = useLibraryStore()
const search = ref('')
const filterCategory = ref<number | null>(null)
const filterTags = ref<number[]>([])

const blocks = computed(() => libraryStore.blocks)
const loading = computed(() => libraryStore.loading)
const categories = computed(() => libraryStore.categories)
const tags = computed(() => libraryStore.tags)

let timeout: ReturnType<typeof setTimeout> | null = null

function debouncedFetch() {
  if (timeout) clearTimeout(timeout)
  timeout = setTimeout(fetchBlocks, 300)
}

async function fetchBlocks() {
  await libraryStore.fetchBlocks({
    search: search.value || undefined,
    category: filterCategory.value ?? undefined,
    tags: filterTags.value.length ? filterTags.value : undefined,
    limit: 50,
  })
}

function onDragStart(event: DragEvent, block: LibraryBlockList) {
  event.dataTransfer?.setData('application/x-library-block-id', String(block.id))
  event.dataTransfer?.setData('application/x-library-block-title', block.title)
  event.dataTransfer?.setData(
    'application/x-library-block-duration',
    String(block.default_duration_minutes ?? 15)
  )
  event.dataTransfer?.setData('application/x-library-block-color', block.color ?? '')

  // Create a styled ghost element for the drag preview
  const ghost = document.createElement('div')
  ghost.style.cssText = `
    position: fixed;
    top: -1000px;
    left: -1000px;
    padding: 6px 10px;
    background: var(--p-primary-color, #3b82f6);
    color: #fff;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    pointer-events: none;
  `
  ghost.textContent = block.title
  document.body.appendChild(ghost)
  event.dataTransfer?.setDragImage(ghost, 0, 0)
  // Clean up after drag
  setTimeout(() => document.body.removeChild(ghost), 0)
}

function formatLastUsed(date: string): string {
  return new Date(date).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

onMounted(async () => {
  await Promise.all([fetchBlocks(), libraryStore.fetchCategories(), libraryStore.fetchTags()])
})
</script>

<style scoped>
.library-picker {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--p-content-background);
  padding: 0.75rem;
  overflow: hidden;
}

.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.picker-header-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.manage-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  color: var(--p-text-muted-color);
  border-radius: 50%;
  transition: background 0.15s, color 0.15s;
  text-decoration: none;
}
.manage-link:hover {
  background: var(--p-content-hover-background);
  color: var(--p-primary-color);
}

.picker-title {
  font-size: 0.95rem;
  font-weight: 600;
  margin: 0;
  color: var(--p-text-color);
}

.loading {
  display: flex;
  justify-content: center;
  padding: 2rem;
}

.picker-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.picker-item {
  border: 1px solid var(--p-content-border-color);
  border-radius: var(--p-border-radius, 6px);
  padding: 0.5rem 0.625rem;
  cursor: grab;
  transition: background 0.1s, box-shadow 0.1s;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  background: var(--p-content-background);
  user-select: none;
}
.picker-item:hover {
  background: var(--p-content-hover-background);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}
.picker-item:active { cursor: grabbing; }

.picker-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.25rem;
}

.picker-item-title {
  font-size: 0.85rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  color: var(--p-text-color);
}

.empty-hint {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  text-align: center;
  padding: 1rem;
}

.picker-item-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.picker-last-used {
  font-size: 0.72rem;
  color: var(--p-text-muted-color);
}

.picker-last-used.never {
  font-style: italic;
  opacity: 0.7;
}
</style>
