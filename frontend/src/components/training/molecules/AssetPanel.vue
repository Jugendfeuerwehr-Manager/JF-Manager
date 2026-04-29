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
import type { TrainingMedia } from '@/types/training'

interface Props {
  blockType: 'library' | 'training'
  blockId: number | null
}

const props = defineProps<Props>()

const fileInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)
const uploading = ref(false)
const mediaItems = ref<TrainingMedia[]>([])

const blockIdRef = ref(props.blockId)
watch(() => props.blockId, (v) => { blockIdRef.value = v; if (v) loadMedia() })

const { uploadImage } = useBlockMediaUpload(props.blockType, blockIdRef)

async function loadMedia() {
  if (!props.blockId) return
  const api = props.blockType === 'library' ? libraryApi : trainingBlocksApi
  const response = await api.listMedia(props.blockId)
  mediaItems.value = response.data
}

watch(() => props.blockId, (id) => { if (id) loadMedia() }, { immediate: true })

function triggerUpload() {
  fileInput.value?.click()
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

.nextcloud-hint {
  display: flex;
  align-items: center;
}

.hidden { display: none; }
</style>
