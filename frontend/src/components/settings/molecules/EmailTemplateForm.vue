<template>
  <div class="template-form">
    <!-- Template Type Selection (for new templates) -->
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

    <!-- Name Field -->
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

    <!-- Active Toggle -->
    <div class="field">
      <div class="checkbox-wrapper">
        <Checkbox
          :modelValue="formData.is_active"
          @update:modelValue="updateField('is_active', $event)"
          inputId="is-active"
          :binary="true"
        />
        <label for="is-active">Vorlage aktivieren</label>
      </div>
    </div>

    <!-- Layout Selection -->
    <div class="field">
      <label for="layout">Layout</label>
      <Select
        id="layout"
        :modelValue="formData.layout ?? 'none'"
        @update:modelValue="updateField('layout', $event)"
        :options="LAYOUT_OPTIONS"
        optionLabel="label"
        optionValue="value"
        class="w-full"
      />
      <small class="layout-hint">Das Layout wird nur bei eigenen Vorlagen angewendet, nicht bei Standard-Vorlagen.</small>
    </div>

    <!-- Subject Template -->
    <div class="field">
      <label for="subject">Betreff-Vorlage *</label>
      <InputText
        id="subject"
        :modelValue="formData.subject_template"
        @update:modelValue="updateField('subject_template', $event)"
        placeholder="z.B. Neue Bestellung #{{ order.pk }}"
        class="w-full"
      />
    </div>

    <!-- HTML Template -->
    <div class="field">
      <label for="html">HTML-Vorlage *</label>
      <MonacoEditor
        :modelValue="formData.html_template"
        @update:modelValue="updateField('html_template', $event)"
        language="html"
        height="500px"
        :wordWrap="'on'"
      />
    </div>

    <!-- Text Template -->
    <div class="field">
      <label for="text">Text-Vorlage (optional)</label>
      <Textarea
        id="text"
        :modelValue="formData.text_template"
        @update:modelValue="updateField('text_template', $event)"
        rows="5"
        placeholder="Text-Fallback für E-Mail-Clients ohne HTML-Unterstützung"
        class="w-full"
      />
    </div>

    <!-- Error Message -->
    <Message v-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>
  </div>
</template>

<script setup lang="ts">
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Message from 'primevue/message'
import MonacoEditor from '@/components/common/MonacoEditor.vue'
import type { EmailTemplateCreateUpdate, TemplateType } from '@/types/email-templates'

const LAYOUT_OPTIONS = [
  { value: 'none', label: 'Kein Layout (reines HTML)' },
  { value: 'general', label: 'Allgemeine Information' },
  { value: 'important', label: 'Wichtige Mitteilung' },
  { value: 'events', label: 'Veranstaltung / Termin' },
]

interface Props {
  formData: EmailTemplateCreateUpdate
  availableTypes: TemplateType[]
  isCreating: boolean
  error?: string | null
}

interface Emits {
  (e: 'update:formData', value: EmailTemplateCreateUpdate): void
  (e: 'typeChange', value: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

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
  gap: 1.5rem;
}

.field label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.layout-hint {
  display: block;
  margin-top: 0.35rem;
  color: var(--p-text-muted-color, #6b7280);
  font-size: 0.8rem;
}
</style>
