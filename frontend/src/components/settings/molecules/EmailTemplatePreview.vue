<template>
  <Card class="preview-card">
    <template #title>
      <div class="flex align-items-center gap-2">
        <i class="pi pi-eye"></i>
        <span>Live-Vorschau</span>
        <ProgressSpinner v-if="loading" style="width: 20px; height: 20px" />
      </div>
    </template>
    <template #content>
      <div v-if="previewData" class="preview-content">
        <div class="preview-section">
          <strong>Betreff:</strong>
          <p>{{ previewData.subject || '(leer)' }}</p>
        </div>
        <Divider />
        <div class="preview-section">
          <strong>HTML-Vorschau:</strong>
          <PhoneMockup
            :subject="previewData.subject"
            :htmlContent="htmlContent"
          />
        </div>
        <Message v-if="previewData.errors && previewData.errors.length" severity="warn" class="mt-2">
          <ul class="m-0 pl-3">
            <li v-for="(err, idx) in previewData.errors" :key="idx">{{ err }}</li>
          </ul>
        </Message>
      </div>
      <div v-else class="empty-state">
        <i class="pi pi-eye-slash" style="font-size: 2rem; color: var(--p-text-muted-color)"></i>
        <p class="text-sm">Vorschau wird beim Tippen aktualisiert</p>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Card from 'primevue/card'
import Divider from 'primevue/divider'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import PhoneMockup from '../atoms/PhoneMockup.vue'
import type { TemplatePreviewResponse } from '@/types/email-templates'

interface Props {
  previewData: TemplatePreviewResponse | null
  loading?: boolean
}

const props = defineProps<Props>()

const htmlContent = computed(() => {
  if (!props.previewData?.html_content) {
    return '<p style="color: #999; padding: 1rem;">(leer)</p>'
  }
  return props.previewData.html_content
})
</script>

<style scoped>
.preview-card {
  height: 100%;
}

.preview-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.preview-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.preview-section strong {
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.preview-section p {
  margin: 0;
  font-weight: 500;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  text-align: center;
  color: var(--p-text-muted-color);
}

.empty-state p {
  margin-top: 1rem;
  margin-bottom: 0;
}
</style>
