<template>
  <section class="library-picker" aria-labelledby="library-picker-title">
    <div class="picker-header">
      <h2 id="library-picker-title" class="picker-title">Bibliothek</h2>
      <div class="picker-header-actions">
        <router-link
          to="/training/library"
          target="_blank"
          class="manage-link"
          aria-label="Bibliothek verwalten (neuer Tab)"
          v-tooltip.bottom="'Bibliothek verwalten'"
        >
          <i class="pi pi-external-link" aria-hidden="true" />
        </router-link>
        <Button icon="pi pi-times" text severity="secondary" aria-label="Bibliothek schließen" @click="emit('close')" />
      </div>
    </div>

    <div class="picker-filters">
      <IconField>
        <InputIcon class="pi pi-search" />
        <InputText v-model="search" placeholder="Baustein suchen …" aria-label="Bausteine durchsuchen" class="w-full" @update:model-value="debouncedFetch" />
      </IconField>
      <Select
        v-model="filterCategory"
        :options="[{ id: null, name: 'Alle Kategorien' }, ...categories]"
        option-label="name"
        option-value="id"
        placeholder="Alle Kategorien"
        aria-label="Kategorie"
        class="w-full"
        @change="fetchBlocks"
      />
      <MultiSelect
        v-model="filterTags"
        :options="tags"
        option-label="name"
        option-value="id"
        placeholder="Tags filtern …"
        aria-label="Tags"
        class="w-full"
        :max-selected-labels="2"
        @change="fetchBlocks"
      />
    </div>

    <p class="picker-hint">Antippen fügt den Baustein ein, Ziehen legt ihn in eine Gruppe.</p>

    <div v-if="loading" class="loading" role="status"><ProgressSpinner style="width:32px;height:32px" aria-label="Bausteine laden" /></div>

    <ul v-else class="picker-list" aria-label="Bausteine">
      <li v-for="block in blocks" :key="block.id">
        <div
          class="picker-item"
          role="button"
          tabindex="0"
          draggable="true"
          :aria-label="`${block.title} einfügen`"
          :aria-describedby="block.description ? `picker-description-${block.id}` : undefined"
          @dragstart="onDragStart($event, block)"
          @click="emit('pick', block)"
          @keydown.enter.prevent="emit('pick', block)"
          @keydown.space.prevent="emit('pick', block)"
        >
          <div class="picker-item-header">
            <span class="picker-item-title">{{ block.title }}</span>
            <BlockDurationBadge v-if="block.default_duration_minutes" :minutes="block.default_duration_minutes" />
          </div>
          <p v-if="block.description" :id="`picker-description-${block.id}`" class="picker-item-description">{{ block.description }}</p>
          <div class="picker-item-meta">
            <LibraryBlockCategoryBadge
              v-if="block.category !== null"
              :category="{ id: block.category!, name: block.category_name ?? '', color: block.category_color ?? '', icon: '' }"
            />
            <span class="picker-last-used">
              {{ block.last_used_date ? `Zuletzt ${formatLastUsed(block.last_used_date)}` : 'Noch nicht verwendet' }}
            </span>
            <span v-if="block.usage_count" class="picker-usage">{{ block.usage_count }} × verwendet</span>
          </div>
          <ul v-if="block.tags?.length" class="picker-item-tags" aria-label="Tags">
            <li v-for="tag in block.tags.slice(0, 4)" :key="tag.id">{{ tag.name }}</li>
            <li v-if="block.tags.length > 4">+{{ block.tags.length - 4 }}</li>
          </ul>
        </div>
      </li>
      <li v-if="!blocks.length" class="empty-hint">Keine Bausteine gefunden.</li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
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

  // Drag preview in the theme's primary colour; tokens resolve because the ghost lives in <body>.
  const ghost = document.createElement('div')
  ghost.style.cssText = `
    position: fixed;
    top: -1000px;
    left: -1000px;
    padding: 6px 10px;
    background: var(--jf-color-primary);
    color: var(--jf-color-on-primary);
    border-radius: var(--jf-radius-md);
    font: 600 13px var(--jf-font-sans);
    white-space: nowrap;
    box-shadow: var(--jf-shadow-lg);
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
  container: library-picker / inline-size;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  height: 100%;
  background: var(--jf-color-card);
  padding: var(--jf-space-2);
  box-sizing: border-box;
  overflow: hidden;
}

.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.picker-header-actions { display: flex; align-items: center; gap: var(--jf-space-0-5); }
.picker-header-actions :deep(.p-button) { min-width: var(--jf-touch-target); min-height: var(--jf-touch-target); }
.picker-title {
  margin: 0;
  font-size: var(--jf-text-lg);
  font-weight: var(--jf-weight-bold);
  color: var(--jf-color-text);
}

.manage-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--jf-touch-target);
  height: var(--jf-touch-target);
  color: var(--jf-color-text-muted);
  border-radius: var(--jf-radius-md);
  text-decoration: none;
  transition: background var(--jf-duration), color var(--jf-duration);
}
.manage-link:hover { background: var(--p-content-hover-background); color: var(--jf-color-text); }
.manage-link:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }

.picker-filters { display: flex; flex-direction: column; gap: var(--jf-space-1); }
.picker-hint { margin: 0; font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }

.loading { display: flex; justify-content: center; padding: var(--jf-space-4); }

.picker-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  margin: 0;
  padding: 2px;
  list-style: none;
}

.picker-item {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  min-height: var(--jf-touch-target);
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  cursor: grab;
  user-select: none;
  transition: background var(--jf-duration), box-shadow var(--jf-duration);
}
.picker-item:hover { background: var(--p-content-hover-background); box-shadow: var(--jf-shadow-sm); }
.picker-item:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
.picker-item:active { cursor: grabbing; }

.picker-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
}
.picker-item-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text);
}
.picker-item-meta { display: flex; align-items: center; flex-wrap: wrap; gap: var(--jf-space-1); }
.picker-last-used,
.picker-usage { font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }

/* UX-09: more about each block; description stays short in the narrow panel */
.picker-item-description {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
  overflow: hidden;
  margin: 0;
  font-size: var(--jf-text-xs);
  line-height: var(--jf-leading-normal);
  color: var(--jf-color-text-muted);
}
.picker-usage { display: none; }
.picker-item-tags {
  display: none;
  flex-wrap: wrap;
  gap: var(--jf-space-0-5);
  margin: 0;
  padding: 0;
  list-style: none;
}
.picker-item-tags li {
  padding: 0 var(--jf-space-0-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-sm);
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
}

/* Wider panel: filters side by side, two-line descriptions, tags and usage */
@container library-picker (min-width: 24rem) {
  .picker-filters { display: grid; grid-template-columns: 1fr 1fr; }
  .picker-filters > :first-child { grid-column: 1 / -1; }
  .picker-item { padding: var(--jf-space-1-5); }
  .picker-item-description { -webkit-line-clamp: 2; line-clamp: 2; }
  .picker-usage { display: inline; }
  .picker-item-tags { display: flex; }
}

/* Very wide panel (large screens): blocks as a two-column grid */
@container library-picker (min-width: 36rem) {
  .picker-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); align-content: start; }
  .picker-item { height: 100%; box-sizing: border-box; }
  .picker-item-description { -webkit-line-clamp: 3; line-clamp: 3; }
  .empty-hint { grid-column: 1 / -1; }
}

.empty-hint {
  padding: var(--jf-space-2);
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
  text-align: center;
}
</style>
