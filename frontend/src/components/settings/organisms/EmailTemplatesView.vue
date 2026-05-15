<template>
  <div class="email-templates-view">
    <div class="header">
      <h2>E-Mail-Vorlagen</h2>
      <Button
        v-if="!selectedTemplateId"
        label="Neue Vorlage"
        icon="pi pi-plus"
        @click="handleCreate"
        :disabled="!hasAvailableTypes"
      />
    </div>

    <!-- Loading State -->
    <div v-if="loading && !templates.length" class="loading-container">
      <ProgressSpinner />
    </div>

    <!-- Step 1: Template List -->
    <div v-else-if="!selectedTemplateId" class="templates-grid">
      <EmailTemplatesList
        :templates="templates"
        @edit="handleEdit"
        @delete="handleDeleteConfirm"
        @create="handleCreate"
      />
    </div>

    <!-- Step 2A: Template Type Selection (for new templates) -->
    <div v-else-if="isCreating && !formData.template_type" class="type-selection">
      <Card>
        <template #title>
          <div class="editor-header">
            <Button
              icon="pi pi-arrow-left"
              text
              @click.prevent="handleBack"
              label="Zurück"
            />
            <span class="flex-1 ml-3">Neue Vorlage - Typ auswählen</span>
          </div>
        </template>
        <template #content>
          <div class="type-selection-content">
            <p class="mb-4">Wählen Sie den Typ der E-Mail-Vorlage aus. Der Inhalt wird automatisch aus der entsprechenden Standard-Vorlage geladen.</p>
            <div class="field">
              <label for="template-type">Vorlagen-Typ</label>
              <Dropdown
                id="template-type"
                v-model="formData.template_type"
                :options="availableTemplateTypes"
                optionLabel="label"
                optionValue="value"
                placeholder="Typ auswählen..."
                @change="handleTypeChange(formData.template_type)"
                class="w-full"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Step 2B: Template Editor with Live Preview (after type selected) -->
    <div v-else class="editor-layout">
      <div class="editor-main">
        <Card class="template-editor">
          <template #title>
            <div class="editor-header">
              <Button
                icon="pi pi-arrow-left"
                text
                @click.prevent="handleBack"
                label="Zurück"
              />
              <span class="flex-1 ml-3">{{ isCreating ? 'Neue Vorlage' : currentTemplate?.template_type_display }}</span>
              <div class="editor-actions">
                <Button
                  label="Speichern"
                  icon="pi pi-save"
                  @click="handleSave"
                  :disabled="!hasChanges || saving"
                  :loading="saving"
                />
              </div>
            </div>
          </template>
          <template #content>
            <EmailTemplateForm
              :formData="formData"
              :availableTypes="availableTemplateTypes"
              :isCreating="isCreating"
              :error="error"
              @update:formData="updateFormData"
              @typeChange="handleTypeChange"
            />
          </template>
        </Card>
      </div>

      <div class="editor-sidebar">
        <!-- Variables Sidebar -->
        <Card class="variables-sidebar">
          <template #title>Verfügbare Variablen</template>
          <template #content>
            <TemplateVariablesList :variables="currentVariables" />
          </template>
        </Card>
        
        <!-- Live Preview -->
        <EmailTemplatePreview
          :previewData="livePreviewData"
          :loading="previewing"
        />
        <div v-if="livePreviewError && !previewing" class="preview-error">
          <i class="pi pi-exclamation-triangle"></i>
          <span>Vorschau nicht verfügbar: {{ livePreviewError }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useEmailTemplatesStore } from '@/stores/email-templates'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Dropdown from 'primevue/dropdown'
import ProgressSpinner from 'primevue/progressspinner'
import EmailTemplatesList from '../molecules/EmailTemplatesList.vue'
import EmailTemplateForm from '../molecules/EmailTemplateForm.vue'
import EmailTemplatePreview from '../molecules/EmailTemplatePreview.vue'
import TemplateVariablesList from '../molecules/TemplateVariablesList.vue'
import type { EmailTemplateCreateUpdate, TemplatePreviewResponse, TemplateVariables } from '@/types/email-templates'

const store = useEmailTemplatesStore()
const confirm = useConfirm()
const toast = useToast()

// State
const selectedTemplateId = ref<number | null>(null)
const isCreating = ref(false)
const formData = ref<EmailTemplateCreateUpdate>({
  name: '',
  template_type: '',
  subject_template: '',
  html_template: '',
  text_template: '',
  layout: 'none',
  is_active: true
})
const originalData = ref<EmailTemplateCreateUpdate | null>(null)
const livePreviewData = ref<TemplatePreviewResponse | null>(null)
const livePreviewError = ref<string | null>(null)
const currentVariables = ref<TemplateVariables | null>(null)
const localPreviewing = ref(false)
let previewTimeout: ReturnType<typeof setTimeout> | null = null

// Computed
const templates = computed(() => store.templates)
const currentTemplate = computed(() => store.currentTemplate)
const templateTypes = computed(() => store.templateTypes)
const loading = computed(() => store.loading)
const saving = computed(() => store.saving)
const previewing = computed(() => localPreviewing.value)
const error = computed(() => store.error)

const availableTemplateTypes = computed(() => {
  const usedTypes = new Set(templates.value.map(t => t.template_type))
  return templateTypes.value.filter(t => !usedTypes.has(t.value))
})

const hasAvailableTypes = computed(() => availableTemplateTypes.value.length > 0)

const hasChanges = computed(() => {
  if (!originalData.value) return false
  return JSON.stringify(formData.value) !== JSON.stringify(originalData.value)
})

const canPreview = computed(() => {
  return formData.value.template_type &&
         formData.value.subject_template &&
         formData.value.html_template
})

// Methods
async function loadInitialData() {
  await Promise.all([
    store.fetchTemplates(),
    store.fetchTemplateTypes(),
    store.fetchAllVariables()
  ])
}

async function handleEdit(id: number) {
  selectedTemplateId.value = id
  isCreating.value = false
  await store.fetchTemplate(id)
  
  if (currentTemplate.value) {
    formData.value = {
      name: currentTemplate.value.name,
      template_type: currentTemplate.value.template_type,
      subject_template: currentTemplate.value.subject_template,
      html_template: currentTemplate.value.html_template,
      text_template: currentTemplate.value.text_template || '',
      layout: currentTemplate.value.layout ?? 'none',
      is_active: currentTemplate.value.is_active
    }
    originalData.value = { ...formData.value }
    
    await loadVariablesForType(currentTemplate.value.template_type)
    updateLivePreview()
  }
}

function handleCreate() {
  selectedTemplateId.value = -1
  isCreating.value = true
  store.clearCurrentTemplate()
  formData.value = {
    name: '',
    template_type: '',
    subject_template: '',
    html_template: '<!DOCTYPE html>\n<html>\n<head>\n  <meta charset="UTF-8">\n  <title>E-Mail</title>\n</head>\n<body>\n  <h1>Hallo {{ member.first_name }},</h1>\n  <p></p>\n</body>\n</html>',
    text_template: '',
    layout: 'none',
    is_active: true
  }
  originalData.value = { ...formData.value }
  currentVariables.value = null
  livePreviewData.value = null
}

function handleBack() {
  selectedTemplateId.value = null
  isCreating.value = false
  store.clearCurrentTemplate()
  formData.value = {
    name: '',
    template_type: '',
    subject_template: '',
    html_template: '',
    text_template: '',
    layout: 'none',
    is_active: true
  }
  originalData.value = null
  currentVariables.value = null
  livePreviewData.value = null
  store.clearError()
}

async function handleSave() {
  try {
    if (isCreating.value) {
      await store.createTemplate(formData.value)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Vorlage wurde erstellt',
        life: 3000
      })
    } else if (currentTemplate.value) {
      await store.updateTemplate(currentTemplate.value.id, formData.value)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Vorlage wurde gespeichert',
        life: 3000
      })
    }
    
    originalData.value = { ...formData.value }
    handleBack()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Vorlage konnte nicht gespeichert werden',
      life: 5000
    })
  }
}

function handleDeleteConfirm(id: number) {
  confirm.require({
    message: 'Möchten Sie diese Vorlage wirklich löschen?',
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, löschen',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      try {
        await store.deleteTemplate(id)
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Vorlage wurde gelöscht',
          life: 3000
        })
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Vorlage konnte nicht gelöscht werden',
          life: 5000
        })
      }
    }
  })
}

function updateFormData(newData: EmailTemplateCreateUpdate) {
  formData.value = newData
  debouncedPreview()
}

async function updateLivePreview() {
  if (!canPreview.value) {
    livePreviewData.value = null
    return
  }
  
  localPreviewing.value = true
  
  try {
    const variables = await store.fetchVariablesForType(formData.value.template_type)
    
    // Try to fetch real data for preview
    let previewData = variables.sample_data
    
    // If template needs order data, fetch a real order
    if (formData.value.template_type.includes('order') || 
        variables.variables.some(v => v.name === 'order')) {
      try {
        const { ordersApi } = await import('@/api/orders')
        const orderResponse = await ordersApi.list({ limit: 1 })
        if (orderResponse.status === 200) {
          const data = orderResponse.data
          if (data.results && data.results.length > 0) {
            const order = data.results[0]!
            previewData = {
              ...variables.sample_data,
              order: order,
              member: order.member || variables.sample_data.member,
              order_url: `${window.location.origin}/orders/${order.id}`,
              domain: window.location.hostname,
              protocol: window.location.protocol.replace(':', ''),
              timestamp: new Date().toISOString()
            }
          }
        }
      } catch (err) {
        console.warn('Failed to fetch real order data, using sample data:', err)
      }
    }
    
    // Call previewTemplate directly without using store's reactive state
    const result = await store.previewTemplate({
      subject_template: formData.value.subject_template,
      html_template: formData.value.html_template,
      text_template: formData.value.text_template,
      sample_data: previewData
    })
    
    // Only update local state, not store state - prevents re-rendering
    livePreviewData.value = result
    livePreviewError.value = null
  } catch (err) {
    console.error('Live preview failed:', err)
    livePreviewData.value = null
    livePreviewError.value = err instanceof Error ? err.message : 'Vorschau konnte nicht geladen werden'
  } finally {
    localPreviewing.value = false
  }
}

function debouncedPreview() {
  if (previewTimeout) {
    clearTimeout(previewTimeout)
  }
  previewTimeout = setTimeout(() => {
    updateLivePreview()
  }, 1000)
}

async function handleTypeChange(templateType: string) {
  if (templateType) {
    // Auto-generate name from template type if creating new template
    if (isCreating.value && !formData.value.name) {
      const typeLabel = templateTypes.value.find(t => t.value === templateType)?.label
      if (typeLabel) {
        formData.value.name = typeLabel
      }
    }
    
    // Load default content from files when creating new template
    if (isCreating.value) {
      try {
        const response = await store.fetchDefaultContent(templateType)
        if (response) {
          formData.value.subject_template = response.subject_template
          formData.value.html_template = response.html_template
          formData.value.text_template = response.text_template
        }
      } catch {
        toast.add({
          severity: 'warn',
          summary: 'Warnung',
          detail: 'Standard-Template konnte nicht geladen werden',
          life: 3000
        })
      }
    }
    
    await loadVariablesForType(templateType)
    updateLivePreview()
  }
}

async function loadVariablesForType(templateType: string) {
  try {
    currentVariables.value = await store.fetchVariablesForType(templateType)
  } catch {
    currentVariables.value = null
  }
}

onMounted(() => {
  loadInitialData()
})
</script>

<style scoped>
.email-templates-view {
  padding: 1.5rem;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

/* Templates Grid (Step 1) */
.templates-grid {
  max-width: 1200px;
}

/* Type Selection (Step 2A - for new templates) */
.type-selection {
  max-width: 800px;
  margin: 0 auto;
}

.type-selection-content {
  padding: 1rem 0;
}

.type-selection-content p {
  color: var(--text-color-secondary);
  line-height: 1.6;
}

/* Editor Layout (Step 2B) */
.editor-layout {
  display: grid;
  grid-template-columns: 1fr 420px;
  gap: 1.5rem;
  align-items: start;
}

.editor-main {
  min-height: 0;
}

.editor-sidebar {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: sticky;
  top: 1rem;
  max-height: calc(100vh - 2rem);
  overflow-y: auto;
}

.template-editor {
  height: 100%;
}

.editor-header {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 1rem;
}

.flex-1 {
  flex: 1;
}

.editor-actions {
  display: flex;
  gap: 0.5rem;
}

.variables-sidebar :deep(.p-card-body),
.variables-sidebar :deep(.p-card-content) {
  max-height: none;
  overflow: visible;
}

/* Responsive */
@media (max-width: 1024px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }
  
  .editor-sidebar {
    position: relative;
    top: 0;
    max-height: none;
  }
}

.preview-error {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: var(--border-radius);
  background: var(--red-50, #fff5f5);
  border: 1px solid var(--red-200, #fed7d7);
  color: var(--red-700, #c53030);
  font-size: 0.875rem;
}
</style>
