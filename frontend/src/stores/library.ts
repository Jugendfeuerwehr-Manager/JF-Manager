import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { libraryCategoriesApi, libraryApi, libraryTagsApi } from '@/api/training'
import type {
  LibraryBlockCategory,
  LibraryBlockCreate,
  LibraryBlockDetail,
  LibraryBlockExportPackage,
  LibraryBlockList,
  LibraryBlockTag,
  LibraryBlockUpdate,
} from '@/types/training'

export const useLibraryStore = defineStore('trainingLibrary', () => {
  // ── State ────────────────────────────────────────────────────────────────
  const blocks = ref<LibraryBlockList[]>([])
  const currentBlock = ref<LibraryBlockDetail | null>(null)
  const categories = ref<LibraryBlockCategory[]>([])
  const tags = ref<LibraryBlockTag[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const totalCount = ref(0)

  // ── Getters ──────────────────────────────────────────────────────────────
  const hasBlocks = computed(() => blocks.value.length > 0)
  const blocksByCategory = computed(() => {
    const map = new Map<number | null, LibraryBlockList[]>()
    for (const b of blocks.value) {
      const key = b.category ?? null
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(b)
    }
    return map
  })

  // ── Actions ──────────────────────────────────────────────────────────────
  async function fetchBlocks(params?: Record<string, unknown>) {
    loading.value = true
    error.value = null
    try {
      const response = await libraryApi.list(params)
      blocks.value = response.data.results
      totalCount.value = response.data.count
      return blocks.value
    } catch (e: unknown) {
      error.value = 'Fehler beim Laden der Bibliotheksblöcke'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchBlock(id: number) {
    loading.value = true
    error.value = null
    try {
      const response = await libraryApi.get(id)
      currentBlock.value = response.data
      return currentBlock.value
    } catch (e: unknown) {
      error.value = 'Fehler beim Laden des Bibliotheksblocks'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createBlock(data: LibraryBlockCreate) {
    saving.value = true
    error.value = null
    try {
      const response = await libraryApi.create(data)
      currentBlock.value = response.data
      const listItem: LibraryBlockList = {
        id: response.data.id,
        export_uuid: response.data.export_uuid,
        title: response.data.title,
        description: response.data.description,
        default_duration_minutes: response.data.default_duration_minutes,
        category: response.data.category?.id ?? null,
        category_name: response.data.category?.name ?? null,
        category_color: response.data.category?.color ?? null,
        tags: response.data.tags,
        color: response.data.color,
        is_public: response.data.is_public,
        created_at: response.data.created_at,
        usage_count: 0,
        last_used_date: null,
      }
      blocks.value.push(listItem)
      return response.data
    } catch (e: unknown) {
      error.value = 'Fehler beim Erstellen des Bibliotheksblocks'
      throw e
    } finally {
      saving.value = false
    }
  }

  async function updateBlock(id: number, data: LibraryBlockUpdate) {
    saving.value = true
    error.value = null
    try {
      const response = await libraryApi.update(id, data)
      currentBlock.value = response.data
      const idx = blocks.value.findIndex((b) => b.id === id)
      if (idx !== -1) {
        const existing = blocks.value[idx] as LibraryBlockList
        blocks.value[idx] = {
          ...existing,
          title: response.data.title,
          description: response.data.description,
          default_duration_minutes: response.data.default_duration_minutes,
          category: response.data.category?.id ?? null,
          category_name: response.data.category?.name ?? null,
          category_color: response.data.category?.color ?? null,
          tags: response.data.tags,
          color: response.data.color,
          is_public: response.data.is_public,
        }
      }
      return response.data
    } catch (e: unknown) {
      error.value = 'Fehler beim Speichern des Bibliotheksblocks'
      throw e
    } finally {
      saving.value = false
    }
  }

  async function deleteBlock(id: number) {
    loading.value = true
    error.value = null
    try {
      await libraryApi.delete(id)
      blocks.value = blocks.value.filter((b) => b.id !== id)
      if (currentBlock.value?.id === id) currentBlock.value = null
    } catch (e: unknown) {
      error.value = 'Fehler beim Löschen des Bibliotheksblocks'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function uploadImage(id: number, file: File) {
    const response = await libraryApi.uploadImage(id, file)
    // Refresh the block to get updated media list
    if (currentBlock.value?.id === id) {
      await fetchBlock(id)
    }
    return response.data
  }

  async function exportBlocks(ids: number[]) {
    const response = await libraryApi.exportBlocks(ids)
    return response.data
  }

  async function importBlocks(pkg: LibraryBlockExportPackage) {
    saving.value = true
    error.value = null
    try {
      const response = await libraryApi.importBlocks(pkg)
      // Refresh list after import
      await fetchBlocks()
      return response.data
    } catch (e: unknown) {
      error.value = 'Fehler beim Importieren'
      throw e
    } finally {
      saving.value = false
    }
  }

  async function fetchCategories() {
    const response = await libraryCategoriesApi.list()
    categories.value = response.data.results
    return categories.value
  }

  async function fetchTags() {
    const response = await libraryTagsApi.list()
    tags.value = response.data.results
    return tags.value
  }

  function clearCurrentBlock() {
    currentBlock.value = null
  }

  return {
    blocks,
    currentBlock,
    categories,
    tags,
    loading,
    saving,
    error,
    totalCount,
    hasBlocks,
    blocksByCategory,
    fetchBlocks,
    fetchBlock,
    createBlock,
    updateBlock,
    deleteBlock,
    uploadImage,
    exportBlocks,
    importBlocks,
    fetchCategories,
    fetchTags,
    clearCurrentBlock,
  }
})
