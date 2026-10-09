<template>
  <div class="template-form">
    <div class="template-form__fields">
      <div v-if="isCreating" class="field">
        <label for="template-type">Vorlagentyp *</label>
        <Select
          id="template-type"
          :modelValue="formData.template_type"
          @update:modelValue="handleTypeChange"
          :options="availableTypes"
          optionLabel="label"
          optionValue="value"
          placeholder="Vorlagentyp auswählen"
          class="w-full"
        />
      </div>
      <div class="field">
        <label for="name">Name *</label>
        <InputText
          id="name"
          :modelValue="formData.name"
          @update:modelValue="updateField('name', $event)"
          placeholder="z.B. Standard-Bestellbestätigung"
          class="w-full"
        />
      </div>
      <div class="field">
        <label for="layout">Layout</label>
        <Select
          id="layout"
          :modelValue="formData.layout ?? 'none'"
          @update:modelValue="updateField('layout', $event)"
          :options="LAYOUT_OPTIONS"
          optionLabel="label"
          optionValue="value"
          aria-describedby="layout-hint"
          class="w-full"
        />
        <small id="layout-hint" class="field__hint">Gilt nur für eigene Vorlagen, nicht für Standardvorlagen.</small>
      </div>
      <div class="field field--switch">
        <ToggleSwitch
          :modelValue="formData.is_active"
          @update:modelValue="updateField('is_active', $event)"
          inputId="is-active"
        />
        <label for="is-active">Vorlage aktiv</label>
      </div>
    </div>

    <div class="field">
      <label for="subject">Betreff *</label>
      <InputText
        id="subject"
        :modelValue="formData.subject_template"
        @update:modelValue="updateField('subject_template', $event)"
        placeholder="z.B. Neue Bestellung #{{ order.pk }}"
        class="w-full template-form__mono"
      />
    </div>

    <section class="template-form__body" aria-labelledby="template-body-label">
      <div class="template-form__body-head">
        <span id="template-body-label" class="field__label">Inhalt *</span>
        <SegmentedControl v-model="bodyMode" :options="BODY_OPTIONS" label="Inhaltsfassung" />
      </div>
      <p v-if="bodyMode === 'text'" class="field__hint">Ersatz für E-Mail-Programme ohne HTML-Darstellung (optional).</p>
      <div class="template-form__code">
        <MonacoEditor
          v-if="bodyMode === 'html'"
          key="html"
          :modelValue="formData.html_template"
          @update:modelValue="updateField('html_template', $event)"
          language="html"
          height="100%"
          :theme="monacoTheme"
          :minimap="false"
          wordWrap="on"
        />
        <MonacoEditor
          v-else
          key="text"
          :modelValue="formData.text_template ?? ''"
          @update:modelValue="updateField('text_template', $event)"
          language="plaintext"
          height="100%"
          :theme="monacoTheme"
          :minimap="false"
          wordWrap="on"
        />
      </div>
    </section>

    <Message v-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import MonacoEditor from '@/components/common/MonacoEditor.vue'
import SegmentedControl, { type SegmentedOption } from '@/components/common/SegmentedControl.vue'
import type { EmailTemplateCreateUpdate, TemplateType } from '@/types/email-templates'

const LAYOUT_OPTIONS = [
  { value: 'none', label: 'Kein Layout (reines HTML)' },
  { value: 'general', label: 'Allgemeine Information' },
  { value: 'important', label: 'Wichtige Mitteilung' },
  { value: 'events', label: 'Veranstaltung / Termin' },
]

type BodyMode = 'html' | 'text'
const BODY_OPTIONS: SegmentedOption<BodyMode>[] = [
  { value: 'html', label: 'HTML' },
  { value: 'text', label: 'Nur Text' },
]

interface Props {
  formData: EmailTemplateCreateUpdate
  availableTypes: TemplateType[]
  isCreating: boolean
  error?: string | null
  monacoTheme?: 'vs' | 'vs-dark'
}

interface Emits {
  (e: 'update:formData', value: EmailTemplateCreateUpdate): void
  (e: 'typeChange', value: string): void
}

const props = withDefaults(defineProps<Props>(), { error: null, monacoTheme: 'vs' })
const emit = defineEmits<Emits>()

const bodyMode = ref<BodyMode>('html')

function handleTypeChange(value: string) {
  emit('update:formData', { ...props.formData, template_type: value })
  emit('typeChange', value)
}

function updateField(field: keyof EmailTemplateCreateUpdate, value: EmailTemplateCreateUpdate[keyof EmailTemplateCreateUpdate]) {
  emit('update:formData', { ...props.formData, [field]: value })
}
</script>

<style scoped>
.template-form {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  height: 100%;
  min-height: 0;
}

.template-form__fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: var(--jf-space-2);
  align-items: start;
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  min-width: 0;
}

.field label,
.field__label {
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text);
}

.field--switch {
  flex-direction: row;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  /* Lines the switch up with the inputs next to it, below their labels. */
  margin-top: calc(var(--jf-text-sm) * 1.5 + var(--jf-space-0-5));
}

.field__hint {
  margin: 0;
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
}

.template-form__mono {
  font-family: var(--jf-font-mono);
  font-size: var(--jf-text-sm);
}

.template-form__body {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  flex: 1;
  min-height: 0;
}

.template-form__body-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
}

.template-form__code {
  flex: 1;
  min-height: 360px;
}

.template-form__code :deep(.monaco-editor-container) {
  border-color: var(--jf-color-border);
  border-radius: var(--jf-radius-md);
}
</style>
