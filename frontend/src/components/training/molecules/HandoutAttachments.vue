<template>
  <div v-if="docs.length" class="handout-attachments">
    <h3>Anhänge</h3>
    <ul>
      <li v-for="att in docs" :key="att.id">
        <a :href="att.file_url ?? '#'" @click.prevent="att.file_url && downloadMedia(att.file_url, att.name)">
          <i :class="att.mime_type === 'application/pdf' ? 'pi pi-file-pdf' : 'pi pi-file'" aria-hidden="true" />
          {{ att.name }}
          <span v-if="att.file_size" class="size">({{ formatSize(att.file_size) }})</span>
        </a>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { downloadMedia } from '@/utils/privateMedia'
import type { BlockAttachment } from '@/types/training'

interface Props {
  attachments?: BlockAttachment[]
}

const props = withDefaults(defineProps<Props>(), { attachments: () => [] })

const docs = computed(() => props.attachments.filter((a) => a.file_url))

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.handout-attachments h3 { margin: var(--jf-space-2) 0 var(--jf-space-1); font-size: 0.95rem; font-weight: 700; }
ul { margin: 0; padding: 0; list-style: none; }
a { color: var(--p-primary-color); text-decoration: none; }
a:hover { text-decoration: underline; }
.size { color: var(--jf-color-text-muted); font-size: 0.8rem; }
</style>
