<template>
  <div class="library-block-list">
    <!-- Toolbar -->
    <div class="list-toolbar">
      <InputText
        v-model="search"
        placeholder="Suchen…"
        class="search-input"
        @update:model-value="debouncedFetch"
      />
      <Select
        v-model="filterCategory"
        :options="[{ id: null, name: 'Alle Kategorien' }, ...categories]"
        option-label="name"
        option-value="id"
        class="filter-select"
        @change="fetchBlocks"
      />
      <div class="spacer" />
      <Button icon="pi pi-plus" label="Neu" @click="openCreate" />
      <Button icon="pi pi-file-export" severity="secondary" label="Import / Export" outlined @click="showImportExport = true" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
    </div>

    <!-- Empty state -->
    <div v-else-if="!blocks.length" class="empty-state">
      <i class="pi pi-book text-5xl mb-3"></i>
      <h3>Keine Bausteine gefunden</h3>
      <p>Erstelle deinen ersten Ausbildungsbaustein.</p>
      <Button label="Baustein erstellen" icon="pi pi-plus" @click="openCreate" />
    </div>

    <!-- Cards grid -->
    <div v-else class="block-grid">
      <LibraryBlockCard
        v-for="block in blocks"
        :key="block.id"
        :block="block"
        :class="{ 'block-selected': props.masterMode && block.id === props.selectedId }"
        @click="openDetail(block)"
        @show-usages="openUsages(block)"
      >
        <template #actions>
          <Button icon="pi pi-pencil" text size="small" @click.stop="openEdit(block)" />
          <Button icon="pi pi-trash" text size="small" severity="danger" @click.stop="confirmDelete(block)" />
        </template>
      </LibraryBlockCard>
    </div>

    <!-- Pagination -->
    <Paginator
      v-if="totalCount > pageSize"
      :rows="pageSize"
      :total-records="totalCount"
      :first="(page - 1) * pageSize"
      @page="onPageChange"
    />

    <!-- Create / Edit dialog -->
    <Dialog
      v-model:visible="showForm"
      :header="editingBlock ? 'Baustein bearbeiten' : 'Baustein erstellen'"
      :style="{ width: '860px' }"
      modal
      :closable="!saving"
    >
      <LibraryBlockForm
        :initial-data="editingBlock"
        @success="onFormSuccess"
        @cancel="showForm = false"
      />
    </Dialog>

    <!-- Import / Export dialog -->
    <LibraryImportExportDialog v-model:visible="showImportExport" @imported="fetchBlocks" />

    <!-- Usages dialog -->
    <Dialog
      v-model:visible="showUsagesDialog"
      :header="`Verwendungen: ${usagesBlock?.title ?? ''}`"
      :style="{ width: '560px' }"
      modal
    >
      <div v-if="usagesLoading" class="usages-loading">
        <ProgressSpinner style="width:32px;height:32px" />
      </div>
      <div v-else-if="!usagesList.length" class="usages-empty">
        Dieser Baustein wurde noch in keiner Trainingseinheit verwendet.
      </div>
      <div v-else class="usages-list">
        <div v-for="session in usagesList" :key="session.id" class="usage-row">
          <span class="usage-date">{{ formatSessionDate(session.date) }}</span>
          <span class="usage-title">{{ session.title }}</span>
        </div>
      </div>
      <template #footer>
        <Button label="Schließen" severity="secondary" @click="showUsagesDialog = false" />
      </template>
    </Dialog>

    <!-- Delete confirm -->
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Paginator from 'primevue/paginator'
import ProgressSpinner from 'primevue/progressspinner'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import LibraryBlockCard from '../molecules/LibraryBlockCard.vue'
import LibraryBlockForm from '../molecules/LibraryBlockForm.vue'
import LibraryImportExportDialog from './LibraryImportExportDialog.vue'
import { useLibraryStore } from '@/stores/library'
import { libraryApi } from '@/api/training'
import type { LibraryBlockList, LibraryBlockDetail, LibraryBlockUsageSession } from '@/types/training'

interface Props {
  masterMode?: boolean
  selectedId?: number | null
}
const props = defineProps<Props>()
const emit = defineEmits<{
  select: [block: LibraryBlockDetail]
  create: []
}>()

const libraryStore = useLibraryStore()
const confirm = useConfirm()
const toast = useToast()

const search = ref('')
const filterCategory = ref<number | null>(null)
const page = ref(1)
const pageSize = 20
const showForm = ref(false)
const showImportExport = ref(false)
const editingBlock = ref<LibraryBlockDetail | null>(null)
const saving = ref(false)

const blocks = computed(() => libraryStore.blocks)
const totalCount = computed(() => libraryStore.totalCount)
const loading = computed(() => libraryStore.loading)
const categories = computed(() => libraryStore.categories)

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function debouncedFetch() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(fetchBlocks, 350)
}

async function fetchBlocks() {
  page.value = 1
  await libraryStore.fetchBlocks({
    search: search.value || undefined,
    category: filterCategory.value ?? undefined,
    limit: pageSize,
    offset: 0,
  })
}

function onPageChange(event: { page: number }) {
  page.value = event.page + 1
  libraryStore.fetchBlocks({
    search: search.value || undefined,
    category: filterCategory.value ?? undefined,
    limit: pageSize,
    offset: event.page * pageSize,
  })
}

function openCreate() {
  if (props.masterMode) {
    emit('create')
    return
  }
  editingBlock.value = null
  showForm.value = true
}

async function openDetail(block: LibraryBlockList) {
  await libraryStore.fetchBlock(block.id)
  const detail = libraryStore.currentBlock
  if (!detail) return
  if (props.masterMode) {
    emit('select', detail)
    return
  }
  editingBlock.value = detail
  showForm.value = true
}

function openEdit(block: LibraryBlockList) {
  openDetail(block)
}

function confirmDelete(block: LibraryBlockList) {
  confirm.require({
    message: `Baustein "${block.title}" wirklich löschen?`,
    header: 'Baustein löschen',
    icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Abbrechen',
    acceptLabel: 'Löschen',
    accept: async () => {
      await libraryStore.deleteBlock(block.id)
      toast.add({ severity: 'success', summary: 'Gelöscht', life: 3000 })
    },
  })
}

function onFormSuccess(_blockId: number) {
  showForm.value = false
  fetchBlocks()
  toast.add({ severity: 'success', summary: 'Gespeichert', life: 3000 })
}

// ── Usages dialog ─────────────────────────────────────────────────────────────
const showUsagesDialog = ref(false)
const usagesBlock = ref<LibraryBlockList | null>(null)
const usagesList = ref<LibraryBlockUsageSession[]>([])
const usagesLoading = ref(false)

async function openUsages(block: LibraryBlockList) {
  usagesBlock.value = block
  showUsagesDialog.value = true
  usagesLoading.value = true
  try {
    const res = await libraryApi.usages(block.id)
    usagesList.value = res.data
  } finally {
    usagesLoading.value = false
  }
}

function formatSessionDate(date: string): string {
  return new Date(date).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

onMounted(async () => {
  await Promise.all([fetchBlocks(), libraryStore.fetchCategories()])
})
</script>

<style scoped>
.library-block-list { display: flex; flex-direction: column; gap: 1rem; }

.list-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}
.search-input { flex: 1; min-width: 200px; }
.filter-select { width: 200px; }
.spacer { flex: 1; }

.loading-state {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  color: var(--p-text-muted-color);
  text-align: center;
  gap: 0.5rem;
}

.block-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

:deep(.block-selected) {
  outline: 2px solid var(--p-primary-500);
  outline-offset: 2px;
  border-radius: 0.5rem;
}

/* Usages dialog */
.usages-loading, .usages-empty {
  padding: 1.5rem;
  text-align: center;
  color: var(--p-text-muted-color);
  display: flex;
  justify-content: center;
}
.usages-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 400px;
  overflow-y: auto;
}
.usage-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  background: var(--p-content-hover-background);
  font-size: 0.9rem;
}
.usage-date {
  font-weight: 600;
  white-space: nowrap;
  color: var(--p-primary-500);
  min-width: 90px;
}
.usage-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
