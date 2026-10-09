<template>
  <div class="template-preview" :aria-busy="loading || undefined">
    <p class="template-preview__status" role="status">
      <template v-if="loading"><i class="pi pi-spin pi-spinner" aria-hidden="true"></i>Vorschau wird aktualisiert …</template>
      <template v-else-if="previewData"><i class="pi pi-check" aria-hidden="true"></i>Mit Beispieldaten berechnet</template>
    </p>
    <template v-if="previewData">
      <div class="template-preview__subject">
        <span class="template-preview__label">Betreff</span>
        <p>{{ previewData.subject || '(leer)' }}</p>
      </div>
      <Message v-if="previewData.errors && previewData.errors.length" severity="warn" :closable="false">
        <ul class="template-preview__errors">
          <li v-for="(err, idx) in previewData.errors" :key="idx">{{ err }}</li>
        </ul>
      </Message>
      <PhoneMockup :subject="previewData.subject" :htmlContent="htmlContent" />
    </template>
    <div v-else-if="!loading" class="template-preview__empty">
      <i class="pi pi-eye-slash" aria-hidden="true"></i>
      <p>Die Vorschau erscheint, sobald Betreff und Inhalt ausgefüllt sind.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Message from 'primevue/message'
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
.template-preview {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
}

.template-preview__status {
  display: flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  min-height: 1.25rem;
  margin: 0;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text-muted);
}

.template-preview__subject {
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
}

.template-preview__label {
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--jf-color-text-muted);
}

.template-preview__subject p {
  margin: 2px 0 0;
  font-weight: var(--jf-weight-semibold);
  overflow-wrap: anywhere;
}

.template-preview__errors {
  margin: 0;
  padding-left: var(--jf-space-2);
}

.template-preview__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--jf-space-1);
  padding: var(--jf-space-5) var(--jf-space-2);
  border: 1px dashed var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  text-align: center;
  color: var(--jf-color-text-muted);
}

.template-preview__empty i { font-size: 1.5rem; }
.template-preview__empty p { margin: 0; font-size: var(--jf-text-sm); }
</style>
