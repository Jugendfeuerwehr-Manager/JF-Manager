<template>
  <Dialog :visible="visible" header="Bibliothek Import / Export" :style="{ width: '560px' }" modal @update:visible="emit('update:visible', $event)">
    <Tabs value="export">
      <TabList>
        <Tab value="export">Exportieren</Tab>
        <Tab value="import">Importieren</Tab>
      </TabList>
      <TabPanels>
        <!-- Export tab -->
        <TabPanel value="export">
          <div class="export-section">
            <p class="text-color-secondary text-sm mb-3">
              Wähle Bausteine aus und exportiere sie als JSON-Datei zum Teilen mit anderen Gruppen.
            </p>
            <div v-if="blocks.length" class="block-select-list">
              <div v-for="block in blocks" :key="block.id" class="block-select-item">
                <Checkbox v-model="selectedIds" :input-id="`blk-${block.id}`" :value="block.id" />
                <label :for="`blk-${block.id}`" class="ml-2">{{ block.title }}</label>
              </div>
            </div>
            <div v-else class="empty-hint">Keine Bausteine vorhanden.</div>
            <div class="action-row mt-4">
              <span class="text-sm text-color-secondary">{{ selectedIds.length }} ausgewählt</span>
              <Button label="JSON herunterladen" icon="pi pi-download" :disabled="!selectedIds.length" :loading="exporting" @click="doExport" />
            </div>
          </div>
        </TabPanel>

        <!-- Import tab -->
        <TabPanel value="import">
          <div class="import-section">
            <p class="text-color-secondary text-sm mb-3">
              Lade eine zuvor exportierte JSON-Datei hoch. Bereits vorhandene Bausteine (gleiche UUID) werden übersprungen.
            </p>
            <FileUpload
              mode="basic"
              accept=".json"
              choose-label="JSON-Datei wählen"
              auto
              custom-upload
              @uploader="onFileUpload"
            />
            <div v-if="importResult" class="import-result mt-3">
              <Message severity="success">
                {{ importResult.created }} erstellt, {{ importResult.updated }} aktualisiert
                <span v-if="importResult.errors.length">, {{ importResult.errors.length }} Fehler</span>
              </Message>
              <div v-if="importResult.errors.length" class="import-errors mt-2">
                <p v-for="err in importResult.errors" :key="err.block" class="text-sm text-red-500">{{ err.error }}</p>
              </div>
            </div>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <template #footer>
      <Button label="Schließen" severity="secondary" outlined @click="emit('update:visible', false)" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Dialog from 'primevue/dialog'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import FileUpload from 'primevue/fileupload'
import Message from 'primevue/message'
import { useLibraryStore } from '@/stores/library'
import type { LibraryImportResult } from '@/types/training'

defineProps<{ visible: boolean }>()
const emit = defineEmits<{
  'update:visible': [v: boolean]
  imported: []
}>()

const libraryStore = useLibraryStore()
const blocks = computed(() => libraryStore.blocks)
const selectedIds = ref<number[]>([])
const exporting = ref(false)
const importResult = ref<LibraryImportResult | null>(null)

onMounted(() => libraryStore.fetchBlocks({ limit: 1000 }))

async function doExport() {
  exporting.value = true
  try {
    const pkg = await libraryStore.exportBlocks(selectedIds.value)
    if (!pkg) return
    const blob = new Blob([JSON.stringify(pkg, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `library-export-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

async function onFileUpload(event: { files: File | File[] }) {
  const file = Array.isArray(event.files) ? event.files[0] : event.files
  if (!file) return
  const text = await file.text()
  const pkg = JSON.parse(text)
  const result = await libraryStore.importBlocks(pkg)
  importResult.value = result
  if (result) emit('imported')
}
</script>

<style scoped>
.block-select-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 280px;
  overflow-y: auto;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  padding: 0.5rem;
}

.block-select-item {
  display: flex;
  align-items: center;
  padding: 0.375rem 0.5rem;
  border-radius: 4px;
}
.block-select-item:hover { background: var(--surface-hover); }

.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.empty-hint {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  text-align: center;
  padding: 1rem;
}
</style>
