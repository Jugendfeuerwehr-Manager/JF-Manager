<template>
  <div class="asset-panel">
    <div class="panel-header">
      <span class="panel-title">Medien</span>
      <Button icon="pi pi-upload" text size="small" label="Bild hochladen" @click="triggerUpload" :loading="uploading" />
      <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFileSelected" />
    </div>

    <!-- Drop zone -->
    <div
      class="drop-zone"
      :class="{ 'drag-active': dragging }"
      @dragover.prevent="dragging = true"
      @dragleave="dragging = false"
      @drop.prevent="onDrop"
    >
      <i class="pi pi-image text-2xl"></i>
      <span>Bild hier ablegen</span>
    </div>

    <!-- Media list -->
    <div v-if="mediaItems.length" class="media-list">
      <div
        v-for="item in mediaItems"
        :key="item.id"
        class="media-item"
        draggable="true"
        @dragstart="onMediaDragStart($event, item)"
      >
        <img :src="item.url" :alt="item.original_filename" class="media-thumb" />
        <div class="media-info">
          <span class="media-name">{{ item.original_filename }}</span>
          <Button
            icon="pi pi-trash"
            severity="danger"
            text
            size="small"
            @click="removeMedia(item.id)"
          />
        </div>
      </div>
    </div>
    <p v-else class="no-media-hint">Noch keine Bilder hochgeladen</p>

    <!-- Documents section -->
    <Divider />
    <div class="panel-header">
      <span class="panel-title">Dokumente</span>
      <Button icon="pi pi-upload" text size="small" label="Dokument hochladen" @click="triggerDocUpload" :loading="uploadingDoc" />
      <input ref="docFileInput" type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.odt,.odp,.ods,.txt" class="hidden" @change="onDocSelected" />
    </div>
    <div
      class="drop-zone doc-drop-zone"
      :class="{ 'drag-active': draggingDoc }"
      @dragover.prevent="draggingDoc = true"
      @dragleave="draggingDoc = false"
      @drop.prevent="onDocDrop"
    >
      <i class="pi pi-file text-2xl"></i>
      <span>Dokument hier ablegen</span>
    </div>
    <div v-if="attachmentItems.length" class="doc-list">
      <div v-for="att in attachmentItems" :key="att.id" class="doc-item">
        <i :class="docIcon(att.mime_type)" class="doc-icon" />
        <div class="doc-info">
          <a :href="att.file_url ?? '#'" target="_blank" rel="noopener" class="doc-name">{{ att.name }}</a>
          <span class="doc-size">{{ formatSize(att.file_size) }}</span>
        </div>
        <Button icon="pi pi-trash" severity="danger" text size="small" @click="removeAttachment(att.id)" />
      </div>
    </div>
    <p v-else class="no-media-hint">Noch keine Dokumente hochgeladen</p>

    <!-- Nextcloud integration hint -->
    <Divider />
    <div class="nextcloud-hint">
      <i class="pi pi-cloud text-lg mr-2"></i>
      <span class="text-sm text-color-secondary">
        Nextcloud-Ordner-Links können im Formular eingetragen werden.
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import { useBlockMediaUpload } from '@/composables/useBlockMediaUpload'
import { trainingBlocksApi, libraryApi } from '@/api/training'
import type { BlockAttachment, TrainingMedia } from '@/types/training'

interface Props {
  blockType: 'library' | 'training'
  blockId: number | null
}

const props = defineProps<Props>()

const fileInput = ref<HTMLInputElement | null>(null)
const docFileInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)
const draggingDoc = ref(false)
const uploading = ref(false)
const uploadingDoc = ref(false)
const mediaItems = ref<TrainingMedia[]>([])
const attachmentItems = ref<BlockAttachment[]>([])

const blockIdRef = ref(props.blockId)
watch(() => props.blockId, (v) => { blockIdRef.value = v; if (v) loadMedia() })

const { uploadImage } = useBlockMediaUpload(props.blockType, blockIdRef)

async function loadMedia() {
  if (!props.blockId) return
  const api = props.blockType === 'library' ? libraryApi : trainingBlocksApi
  const [mediaRes, attachRes] = await Promise.all([
    api.listMedia(props.blockId),
    api.getAttachments(props.blockId),
  ])
  mediaItems.value = mediaRes.data
  attachmentItems.value = attachRes.data
}

watch(() => props.blockId, (id) => { if (id) loadMedia() }, { immediate: true })

function triggerUpload() {
  fileInput.value?.click()
}

function triggerDocUpload() {
  docFileInput.value?.click()
}

async function onFileSelected(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  await doUpload(file)
  if (fileInput.value) fileInput.value.value = ''
}

async function onDrop(event: DragEvent) {
  dragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (!file?.type.startsWith('image/')) return
  await doUpload(file)
}

async function doUpload(file: File) {
  uploading.value = true
  try {
    const media = await uploadImage(file)
    mediaItems.value.push(media)
  } finally {
    uploading.value = false
  }
}

async function removeMedia(mediaId: number) {
  const api = props.blockType === 'library' ? libraryApi : trainingBlocksApi
  await api.deleteMedia(props.blockId!, mediaId)
  mediaItems.value = mediaItems.value.filter((m) => m.id !== mediaId)
}

function onMediaDragStart(event: DragEvent, item: TrainingMedia) {
  event.dataTransfer?.setData('text/plain', `<img src="${item.url}" alt="${item.original_filename}" />`)
}

async function onDocSelected(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  await doDocUpload(file)
  if (docFileInput.value) docFileInput.value.value = ''
}

async function onDocDrop(event: DragEvent) {
  draggingDoc.value = false
  const file = event.dataTransfer?.files?.[0]
  if (!file || file.type.startsWith('image/')) return
  await doDocUpload(file)
}

async function doDocUpload(file: File) {
  if (!props.blockId) return
  uploadingDoc.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', file.name)
    const api = props.blockType === 'library' ? libraryApi : trainingBlocksApi
    const res = await api.addAttachment(props.blockId, formData)
    attachmentItems.value.push(res.data)
  } finally {
    uploadingDoc.value = false
  }
}

async function removeAttachment(attachmentId: number) {
  const api = props.blockType === 'library' ? libraryApi : trainingBlocksApi
  await api.deleteAttachment(props.blockId!, attachmentId)
  attachmentItems.value = attachmentItems.value.filter((a) => a.id !== attachmentId)
}

function docIcon(mimeType: string | null): string {
  if (!mimeType) return 'pi pi-file'
  if (mimeType === 'application/pdf') return 'pi pi-file-pdf'
  if (mimeType.includes('word') || mimeType.includes('document')) return 'pi pi-file-word'
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return 'pi pi-file-excel'
  if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return 'pi pi-chart-bar'
  return 'pi pi-file'
}

function formatSize(bytes: number | null): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.asset-panel {
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-card);
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.panel-title { font-weight: 600; font-size: 0.9rem; }

.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  border: 2px dashed var(--surface-border);
  border-radius: var(--border-radius);
  padding: 1.25rem;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}
.drop-zone.drag-active {
  border-color: var(--primary-color);
  background: var(--primary-50, #eff6ff);
  color: var(--primary-color);
}

.doc-drop-zone {
  padding: 0.85rem;
}

.media-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  overflow-y: auto;
  max-height: 360px;
}

.media-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  cursor: grab;
}
.media-item:active { cursor: grabbing; }

.media-thumb {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
}

.media-info {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
}

.media-name {
  font-size: 0.8rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.no-media-hint {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  text-align: center;
  margin: 0;
}

.doc-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  overflow-y: auto;
  max-height: 240px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
}

.doc-icon {
  font-size: 1.25rem;
  color: var(--text-color-secondary);
  flex-shrink: 0;
}

.doc-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.doc-name {
  font-size: 0.85rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--primary-color);
  text-decoration: none;
}
.doc-name:hover { text-decoration: underline; }

.doc-size {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.nextcloud-hint {
  display: flex;
  align-items: center;
}

.hidden { display: none; }
</style>
