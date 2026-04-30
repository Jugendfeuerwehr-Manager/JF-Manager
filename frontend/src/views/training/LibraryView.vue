<template>
  <div class="library-view">
    <!-- ── Page header (Groups-style) ── -->
    <div class="page-header">
      <div class="header-left">
        <Button
          icon="pi pi-arrow-left"
          text
          rounded
          size="small"
          v-tooltip.bottom="'Zurück'"
          aria-label="Zurück"
          @click="router.back()"
        />
        <h1 class="page-title">
          <i class="pi pi-book title-icon"></i>
          Ausbildungsbibliothek
        </h1>
        <Tag
          :value="`${libraryStore.totalCount} Bausteine`"
          severity="secondary"
          class="total-tag"
        />
      </div>
      <div class="header-right">
        <Button
          label="Neuer Baustein"
          icon="pi pi-plus"
          @click="onCreateNew"
        />
      </div>
    </div>

    <!-- ── Tabs ── -->
    <div class="library-tabs-wrap">
      <Tabs v-model:value="activeTab" class="library-tabs">
        <TabList>
          <Tab value="blocks"><i class="pi pi-book mr-2" />Bausteine</Tab>
          <Tab value="categories"><i class="pi pi-tag mr-2" />Kategorien</Tab>
          <Tab value="tags"><i class="pi pi-hashtag mr-2" />Tags</Tab>
        </TabList>

        <TabPanels class="tabs-panels">
          <!-- ── Blocks: master-detail ── -->
          <TabPanel value="blocks">
            <div class="master-detail">
              <!-- Left: block list -->
              <div class="master-panel">
                <LibraryBlockList
                  master-mode
                  :selected-id="detailBlock?.id ?? null"
                  @select="onBlockSelect"
                  @create="onCreateNew"
                />
              </div>

              <!-- Right: form / empty state -->
              <div class="detail-panel">
                <div v-if="!detailBlock && !showCreateForm" class="detail-empty">
                  <i class="pi pi-book detail-empty-icon" />
                  <p class="detail-empty-hint">Baustein aus der Liste auswählen<br>oder neuen Baustein erstellen</p>
                  <Button label="Neuer Baustein" icon="pi pi-plus" outlined @click="onCreateNew" />
                </div>
                <LibraryBlockForm
                  v-else
                  :key="detailBlock?.id ?? 'new'"
                  :initial-data="detailBlock"
                  @success="onFormSuccess"
                  @cancel="closeDetail"
                />
              </div>
            </div>
          </TabPanel>

          <!-- ── Categories ── -->
          <TabPanel value="categories">
            <div class="mgmt-section">
              <div class="mgmt-toolbar">
                <h3 class="mgmt-title"><i class="pi pi-tag title-icon"></i>Kategorien</h3>
                <Button icon="pi pi-plus" label="Neue Kategorie" size="small" @click="openCategoryForm(null)" />
              </div>

              <DataTable :value="categories" :loading="catLoading" class="mgmt-table">
                <Column header="Farbe" style="width: 64px">
                  <template #body="{ data }">
                    <div class="color-swatch" :style="{ background: data.color || '#94a3b8' }" />
                  </template>
                </Column>
                <Column field="name" header="Name" />
                <Column header="Icon" style="width: 80px">
                  <template #body="{ data }">
                    <i v-if="data.icon" :class="`pi ${data.icon}`" />
                    <span v-else class="text-muted">–</span>
                  </template>
                </Column>
                <Column header="" style="width: 100px">
                  <template #body="{ data }">
                    <Button icon="pi pi-pencil" text rounded size="small" @click="openCategoryForm(data)" />
                    <Button icon="pi pi-trash" text rounded size="small" severity="danger" @click="deleteCategory(data)" />
                  </template>
                </Column>
              </DataTable>

              <Dialog v-model:visible="showCategoryForm" :header="editingCategory?.id ? 'Kategorie bearbeiten' : 'Neue Kategorie'" :style="{ width: '420px' }" modal>
                <div class="form-fields">
                  <div class="form-field">
                    <label>Name</label>
                    <InputText v-model="categoryForm.name" class="w-full" autofocus />
                  </div>
                  <div class="form-field">
                    <label>Farbe</label>
                    <div class="color-row">
                      <input type="color" v-model="categoryForm.color" class="color-picker" />
                      <span>{{ categoryForm.color }}</span>
                    </div>
                  </div>
                  <div class="form-field">
                    <label>Icon (PrimeIcons, z. B. pi-fire)</label>
                    <InputText v-model="categoryForm.icon" placeholder="pi-fire" class="w-full" />
                  </div>
                </div>
                <template #footer>
                  <Button label="Abbrechen" severity="secondary" outlined @click="showCategoryForm = false" />
                  <Button label="Speichern" icon="pi pi-check" :loading="catSaving" @click="saveCategory" />
                </template>
              </Dialog>
            </div>
          </TabPanel>

          <!-- ── Tags ── -->
          <TabPanel value="tags">
            <div class="mgmt-section">
              <div class="mgmt-toolbar">
                <h3 class="mgmt-title"><i class="pi pi-hashtag title-icon"></i>Tags</h3>
              </div>

              <div class="tag-editor">
                <div class="tag-chips">
                  <Tag v-for="tag in tags" :key="tag.id" class="tag-chip">
                    <template #default>
                      {{ tag.name }}
                      <button class="tag-remove" @click="deleteTag(tag)">×</button>
                    </template>
                  </Tag>
                  <span v-if="!tags.length" class="text-muted text-sm">Keine Tags vorhanden.</span>
                </div>
                <div class="tag-add-row">
                  <InputText v-model="newTagName" placeholder="Neuen Tag eingeben…" @keydown.enter="addTag" />
                  <Button icon="pi pi-plus" label="Hinzufügen" size="small" :loading="tagSaving" @click="addTag" />
                </div>
              </div>
            </div>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>

    <ConfirmDialog />
    <Toast />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ConfirmDialog from 'primevue/confirmdialog'
import Toast from 'primevue/toast'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import LibraryBlockList from '@/components/training/organisms/LibraryBlockList.vue'
import LibraryBlockForm from '@/components/training/molecules/LibraryBlockForm.vue'
import { useLibraryStore } from '@/stores/library'
import { libraryCategoriesApi, libraryTagsApi } from '@/api/training'
import type { LibraryBlockCategory, LibraryBlockTag, LibraryBlockDetail } from '@/types/training'

const router = useRouter()
const libraryStore = useLibraryStore()
const confirm = useConfirm()
const toast = useToast()
const { categories, tags } = storeToRefs(libraryStore)

const activeTab = ref('blocks')

// ── Master-detail ─────────────────────────────────────────────────────────────
const detailBlock = ref<LibraryBlockDetail | null>(null)
const showCreateForm = ref(false)

function onBlockSelect(block: LibraryBlockDetail) {
  detailBlock.value = block
  showCreateForm.value = false
}

function onCreateNew() {
  detailBlock.value = null
  showCreateForm.value = true
  activeTab.value = 'blocks'
}

function closeDetail() {
  detailBlock.value = null
  showCreateForm.value = false
}

function onFormSuccess(_blockId: number) {
  libraryStore.fetchBlocks({ limit: 20 })
  if (!detailBlock.value) showCreateForm.value = false
  toast.add({ severity: 'success', summary: 'Gespeichert', life: 3000 })
}

// ── Category management ───────────────────────────────────────────────────────
const catLoading = ref(false)
const catSaving = ref(false)
const showCategoryForm = ref(false)
const editingCategory = ref<LibraryBlockCategory | null>(null)
const categoryForm = ref({ name: '', color: '#3b82f6', icon: '' })

function openCategoryForm(cat: LibraryBlockCategory | null) {
  editingCategory.value = cat
  categoryForm.value = cat
    ? { name: cat.name, color: cat.color || '#3b82f6', icon: cat.icon || '' }
    : { name: '', color: '#3b82f6', icon: '' }
  showCategoryForm.value = true
}

async function saveCategory() {
  if (!categoryForm.value.name.trim()) return
  catSaving.value = true
  try {
    if (editingCategory.value?.id) {
      await libraryCategoriesApi.update(editingCategory.value.id, categoryForm.value)
      toast.add({ severity: 'success', summary: 'Kategorie gespeichert', life: 3000 })
    } else {
      await libraryCategoriesApi.create(categoryForm.value)
      toast.add({ severity: 'success', summary: 'Kategorie erstellt', life: 3000 })
    }
    showCategoryForm.value = false
    await libraryStore.fetchCategories()
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler beim Speichern', life: 4000 })
  } finally {
    catSaving.value = false
  }
}

function deleteCategory(cat: LibraryBlockCategory) {
  confirm.require({
    message: `Kategorie "${cat.name}" wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      try {
        await libraryCategoriesApi.delete(cat.id)
        await libraryStore.fetchCategories()
        toast.add({ severity: 'success', summary: 'Gelöscht', life: 3000 })
      } catch {
        toast.add({ severity: 'error', summary: 'Fehler beim Löschen', life: 4000 })
      }
    },
  })
}

// ── Tag management ────────────────────────────────────────────────────────────
const tagSaving = ref(false)
const newTagName = ref('')

async function addTag() {
  const name = newTagName.value.trim()
  if (!name) return
  tagSaving.value = true
  try {
    await libraryTagsApi.create({ name })
    newTagName.value = ''
    await libraryStore.fetchTags()
    toast.add({ severity: 'success', summary: 'Tag erstellt', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler beim Erstellen', life: 4000 })
  } finally {
    tagSaving.value = false
  }
}

function deleteTag(tag: LibraryBlockTag) {
  confirm.require({
    message: `Tag "${tag.name}" wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      try {
        await libraryTagsApi.delete(tag.id)
        await libraryStore.fetchTags()
        toast.add({ severity: 'success', summary: 'Gelöscht', life: 3000 })
      } catch {
        toast.add({ severity: 'error', summary: 'Fehler beim Löschen', life: 4000 })
      }
    },
  })
}

onMounted(async () => {
  await Promise.all([libraryStore.fetchCategories(), libraryStore.fetchTags()])
})
</script>

<style scoped>
/* ─── Layout ──────────────────────────────────────────────────────────────── */
.library-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* ─── Header (mirrors GroupManagementView) ────────────────────────────────── */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem 1.5rem 1rem;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.page-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-color);
}

.title-icon {
  color: var(--p-primary-500);
  font-size: 1rem;
}

.total-tag {
  font-size: 0.8rem;
}

/* ─── Tabs ────────────────────────────────────────────────────────────────── */
.library-tabs-wrap {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0 1.5rem 1.5rem;
}

.library-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
}

:deep(.tabs-panels) {
  flex: 1;
  overflow: hidden;
}

:deep(.p-tabpanel) {
  height: 100%;
  overflow: hidden;
}

/* ─── Master-detail (Blocks tab) ─────────────────────────────────────────── */
.master-detail {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 0;
  height: calc(100vh - 200px);
  min-height: 500px;
  border: 1px solid var(--p-content-border-color);
  border-radius: 0.5rem;
  overflow: hidden;
  background: var(--p-content-background);
}

.master-panel {
  border-right: 1px solid var(--p-content-border-color);
  overflow-y: auto;
  background: var(--p-content-hover-background);
  padding: 1rem;
}

.detail-panel {
  overflow-y: auto;
  padding: 1.5rem;
}

.detail-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
  color: var(--p-text-muted-color);
  text-align: center;
}

.detail-empty-icon {
  font-size: 3rem;
  opacity: 0.35;
}

.detail-empty-hint {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.6;
}

/* ─── Mgmt sections (Categories / Tags) ──────────────────────────────────── */
.mgmt-section {
  padding: 1rem 0;
  max-width: 800px;
}

.mgmt-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.mgmt-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--p-text-color);
}

.mgmt-table {
  font-size: 0.9rem;
}

.color-swatch {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: 1px solid var(--p-content-border-color);
}

.text-muted {
  color: var(--p-text-muted-color);
}

/* ─── Form fields (in dialogs) ────────────────────────────────────────────── */
.form-fields {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-bottom: 0.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-field label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--p-text-muted-color);
}

.color-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.color-picker {
  width: 2.5rem;
  height: 2rem;
  border: none;
  background: none;
  cursor: pointer;
}

/* ─── Tag editor ──────────────────────────────────────────────────────────── */
.tag-editor {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.tag-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  min-height: 40px;
}

.tag-chip {
  cursor: default;
}

.tag-remove {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  padding: 0 0 0 4px;
  color: inherit;
  opacity: 0.7;
}

.tag-remove:hover {
  opacity: 1;
}

.tag-add-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  max-width: 400px;
}
</style>
