<template>
  <div class="template-workspace" @keydown="onKeydown">
    <WorkspaceHeader
      :title="headerTitle"
      :back-to="{ name: 'settings-email-templates' }"
      back-label="E-Mail-Vorlagen"
      :eyebrow="isCreating ? 'Neue Vorlage' : currentTemplate?.name"
    >
      <template v-if="!isCreating && currentTemplate" #meta>
        <StatusBadge
          :label="formData.is_active ? 'Aktiv' : 'Inaktiv'"
          :severity="formData.is_active ? 'success' : 'neutral'"
        />
        <span>Zuletzt geändert {{ formatDate(currentTemplate.updated_at) }}</span>
      </template>
      <template v-if="showEditor" #status>
        <span class="save-hint" :class="{ 'save-hint--dirty': hasChanges }" role="status">
          <template v-if="saving">Speichert …</template>
          <template v-else-if="hasChanges"><i class="pi pi-pencil" aria-hidden="true"></i>Ungespeicherte Änderungen</template>
          <template v-else-if="!isCreating"><i class="pi pi-check" aria-hidden="true"></i>Alles gespeichert</template>
        </span>
      </template>
      <template v-if="showEditor" #actions>
        <Button
          label="Speichern"
          icon="pi pi-save"
          :disabled="!canSave"
          :loading="saving"
          v-tooltip.bottom="'Strg + S'"
          @click="handleSave"
        />
      </template>
    </WorkspaceHeader>

    <div v-if="loadState" class="template-workspace__state">
      <StateView :kind="loadState" :message="loadState === 'loading' ? undefined : loadError ?? undefined" @retry="load" />
    </div>

    <div v-else-if="isCreating && !formData.template_type" class="template-workspace__state">
      <section class="type-step" aria-labelledby="type-step-title">
        <h2 id="type-step-title" class="type-step__title">Welche E-Mail soll die Vorlage ersetzen?</h2>
        <p class="type-step__text">Der Inhalt wird aus der Standardvorlage dieses Typs übernommen und kann danach angepasst werden.</p>
        <label for="template-type-step" class="type-step__label">Vorlagentyp</label>
        <Select
          id="template-type-step"
          :modelValue="formData.template_type"
          :options="availableTemplateTypes"
          optionLabel="label"
          optionValue="value"
          placeholder="Typ auswählen …"
          class="w-full"
          @update:modelValue="selectType"
        />
        <p v-if="!availableTemplateTypes.length" class="type-step__text">Für alle Typen gibt es bereits eine eigene Vorlage.</p>
      </section>
    </div>

    <div v-else class="template-workspace__body">
      <section class="template-workspace__main" aria-label="Vorlage bearbeiten">
        <EmailTemplateForm
          :formData="formData"
          :availableTypes="availableTemplateTypes"
          :isCreating="isCreating"
          :error="error"
          :monacoTheme="isDark ? 'vs-dark' : 'vs'"
          @update:formData="updateFormData"
          @typeChange="handleTypeChange"
        />
      </section>

      <aside class="template-workspace__side" aria-label="Vorschau und Variablen">
        <SegmentedControl v-model="sidePanel" :options="sideOptions" label="Seitenbereich" />
        <template v-if="sidePanel === 'preview'">
          <EmailTemplatePreview :previewData="livePreviewData" :loading="previewing" />
          <Message v-if="livePreviewError && !previewing" severity="warn" :closable="false">
            Vorschau nicht verfügbar: {{ livePreviewError }}
          </Message>
        </template>
        <TemplateVariablesList v-else :variables="currentVariables" />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { format } from 'date-fns'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Select from 'primevue/select'
import { useEmailTemplatesStore } from '@/stores/email-templates'
import WorkspaceHeader from '@/components/common/WorkspaceHeader.vue'
import SegmentedControl, { type SegmentedOption } from '@/components/common/SegmentedControl.vue'
import StateView, { stateForError, type StateKind } from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EmailTemplateForm from '../molecules/EmailTemplateForm.vue'
import EmailTemplatePreview from '../molecules/EmailTemplatePreview.vue'
import TemplateVariablesList from '../molecules/TemplateVariablesList.vue'
import { classifyApiError } from '@/utils/apiError'
import type { EmailTemplateCreateUpdate, TemplatePreviewResponse, TemplateVariables } from '@/types/email-templates'

const props = defineProps<{
  /** `null` creates a new template. */
  templateId: number | null
}>()

const store = useEmailTemplatesStore()
const router = useRouter()
const toast = useToast()

const EMPTY_HTML = '<!DOCTYPE html>\n<html>\n<head>\n  <meta charset="UTF-8">\n  <title>E-Mail</title>\n</head>\n<body>\n  <h1>Hallo {{ member.first_name }},</h1>\n  <p></p>\n</body>\n</html>'

function emptyForm(): EmailTemplateCreateUpdate {
  return { name: '', template_type: '', subject_template: '', html_template: EMPTY_HTML, text_template: '', layout: 'none', is_active: true }
}

const formData = ref<EmailTemplateCreateUpdate>(emptyForm())
const originalData = ref<EmailTemplateCreateUpdate>(emptyForm())
const livePreviewData = ref<TemplatePreviewResponse | null>(null)
const livePreviewError = ref<string | null>(null)
const currentVariables = ref<TemplateVariables | null>(null)
const previewing = ref(false)
const loadState = ref<StateKind | null>('loading')
const loadError = ref<string | null>(null)
const sidePanel = ref<'preview' | 'variables'>('preview')
let previewTimeout: ReturnType<typeof setTimeout> | null = null

const isCreating = computed(() => props.templateId === null)
const currentTemplate = computed(() => (isCreating.value ? null : store.currentTemplate))
const saving = computed(() => store.saving)
const error = computed(() => store.error)
const showEditor = computed(() => !loadState.value && !(isCreating.value && !formData.value.template_type))

const availableTemplateTypes = computed(() => {
  const usedTypes = new Set(store.templates.map((t) => t.template_type))
  return store.templateTypes.filter((t) => !usedTypes.has(t.value))
})

const headerTitle = computed(() => {
  const type = formData.value.template_type
  const label = currentTemplate.value?.template_type_display ?? store.templateTypes.find((t) => t.value === type)?.label
  return label ?? (isCreating.value ? 'Neue E-Mail-Vorlage' : 'E-Mail-Vorlage')
})

const hasChanges = computed(() => JSON.stringify(formData.value) !== JSON.stringify(originalData.value))
const canSave = computed(() =>
  hasChanges.value && !saving.value && !!formData.value.name?.trim() && !!formData.value.subject_template.trim() && !!formData.value.html_template.trim(),
)
const canPreview = computed(() => !!(formData.value.template_type && formData.value.subject_template && formData.value.html_template))

const sideOptions = computed<SegmentedOption<'preview' | 'variables'>[]>(() => [
  { value: 'preview', label: 'Vorschau' },
  { value: 'variables', label: 'Variablen', count: currentVariables.value?.variables.length ?? null },
])

// Monaco has its own themes; follow the app's dark class.
const isDark = ref(document.documentElement.classList.contains('app-dark'))
const themeObserver = new MutationObserver(() => {
  isDark.value = document.documentElement.classList.contains('app-dark')
})

async function load() {
  loadState.value = 'loading'
  loadError.value = null
  try {
    await Promise.all([store.fetchTemplates(), store.fetchTemplateTypes()])
    if (props.templateId === null) {
      store.clearCurrentTemplate()
      formData.value = emptyForm()
      originalData.value = emptyForm()
    } else {
      const template = await store.fetchTemplate(props.templateId)
      formData.value = {
        name: template.name,
        template_type: template.template_type,
        subject_template: template.subject_template,
        html_template: template.html_template,
        text_template: template.text_template || '',
        layout: template.layout ?? 'none',
        is_active: template.is_active,
      }
      originalData.value = { ...formData.value }
      await loadVariablesForType(template.template_type)
      void updateLivePreview()
    }
    loadState.value = null
  } catch (err) {
    loadState.value = stateForError(classifyApiError(err))
    loadError.value = store.error
  }
}

async function handleSave() {
  if (!canSave.value) return
  try {
    if (isCreating.value) {
      const created = await store.createTemplate(formData.value)
      originalData.value = { ...formData.value }
      toast.add({ severity: 'success', summary: 'Gespeichert', detail: 'Vorlage wurde erstellt.', life: 3000 })
      await router.replace({ name: 'email-template-edit', params: { id: created.id } })
    } else if (props.templateId !== null) {
      await store.updateTemplate(props.templateId, formData.value)
      originalData.value = { ...formData.value }
      toast.add({ severity: 'success', summary: 'Gespeichert', detail: 'Vorlage wurde gespeichert.', life: 3000 })
    }
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Vorlage konnte nicht gespeichert werden.', life: 5000 })
  }
}

function onKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    void handleSave()
  }
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
  previewing.value = true
  try {
    const variables = await store.fetchVariablesForType(formData.value.template_type)
    let previewData = variables.sample_data

    // Order mails read better with a real order than with sample data.
    if (formData.value.template_type.includes('order') || variables.variables.some((v) => v.name === 'order')) {
      try {
        const { ordersApi } = await import('@/api/orders')
        const orderResponse = await ordersApi.list({ limit: 1 })
        const order = orderResponse.status === 200 ? orderResponse.data.results?.[0] : undefined
        if (order) {
          previewData = {
            ...variables.sample_data,
            order,
            member: order.member || variables.sample_data.member,
            order_url: `${window.location.origin}/orders/${order.id}`,
            domain: window.location.hostname,
            protocol: window.location.protocol.replace(':', ''),
            timestamp: new Date().toISOString(),
          }
        }
      } catch (err) {
        console.warn('Failed to fetch real order data, using sample data:', err)
      }
    }

    livePreviewData.value = await store.previewTemplate({
      subject_template: formData.value.subject_template,
      html_template: formData.value.html_template,
      text_template: formData.value.text_template,
      sample_data: previewData,
    })
    livePreviewError.value = null
  } catch (err) {
    livePreviewData.value = null
    livePreviewError.value = err instanceof Error ? err.message : 'Vorschau konnte nicht geladen werden'
  } finally {
    previewing.value = false
  }
}

function debouncedPreview() {
  if (previewTimeout) clearTimeout(previewTimeout)
  previewTimeout = setTimeout(() => void updateLivePreview(), 1000)
}

function selectType(templateType: string) {
  formData.value = { ...formData.value, template_type: templateType }
  void handleTypeChange(templateType)
}

async function handleTypeChange(templateType: string) {
  if (!templateType) return
  if (isCreating.value) {
    const typeLabel = store.templateTypes.find((t) => t.value === templateType)?.label
    if (typeLabel && !formData.value.name) formData.value = { ...formData.value, name: typeLabel }
    try {
      const response = await store.fetchDefaultContent(templateType)
      if (response) {
        formData.value = {
          ...formData.value,
          subject_template: response.subject_template,
          html_template: response.html_template,
          text_template: response.text_template,
        }
      }
    } catch {
      toast.add({ severity: 'warn', summary: 'Hinweis', detail: 'Standardvorlage konnte nicht geladen werden.', life: 3000 })
    }
  }
  await loadVariablesForType(templateType)
  void updateLivePreview()
}

async function loadVariablesForType(templateType: string) {
  try {
    currentVariables.value = await store.fetchVariablesForType(templateType)
  } catch {
    currentVariables.value = null
  }
}

function formatDate(dateString: string): string {
  return format(new Date(dateString), 'dd.MM.yyyy, HH:mm')
}

function allowLeave() {
  return saving.value ? false : !hasChanges.value || window.confirm('Ungespeicherte Änderungen an der Vorlage verwerfen?')
}
onBeforeRouteLeave(allowLeave)

function beforeUnload(event: BeforeUnloadEvent) {
  if (hasChanges.value || saving.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}

onMounted(() => {
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  window.addEventListener('beforeunload', beforeUnload)
  void load()
})

onBeforeUnmount(() => {
  themeObserver.disconnect()
  window.removeEventListener('beforeunload', beforeUnload)
  if (previewTimeout) clearTimeout(previewTimeout)
  store.clearError()
})
</script>

<style scoped>
.template-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--jf-color-ground);
}

.template-workspace__state {
  flex: 1;
  padding: var(--jf-space-4) var(--jf-space-3);
}

.template-workspace__body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(340px, 30vw, 440px);
}

.template-workspace__main {
  min-height: 0;
  overflow-y: auto;
  padding: var(--jf-space-2) var(--jf-space-3);
  background: var(--jf-color-card);
}

.template-workspace__side {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  min-height: 0;
  overflow-y: auto;
  padding: var(--jf-space-2);
  border-left: 1px solid var(--jf-color-border);
  background: var(--jf-color-ground);
}

.type-step {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  max-width: 36rem;
  margin: 0 auto;
  padding: var(--jf-space-3);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  box-shadow: var(--jf-shadow-sm);
}

.type-step__title { margin: 0; font-size: var(--jf-text-lg); }
.type-step__text { margin: 0 0 var(--jf-space-1); font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.type-step__label { font-size: var(--jf-text-sm); font-weight: var(--jf-weight-semibold); }

.save-hint {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  margin-right: var(--jf-space-0-5);
  font-size: 0.8125rem;
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text-muted);
}
.save-hint--dirty { color: var(--p-amber-800); }
.app-dark .save-hint--dirty { color: var(--p-amber-300); }

/* Below desktop width the panels stack and the page scrolls as a whole. */
@media (max-width: 1023px) {
  .template-workspace { height: auto; }
  .template-workspace__body { grid-template-columns: minmax(0, 1fr); }
  .template-workspace__main,
  .template-workspace__side { overflow: visible; }
  .template-workspace__side { border-left: 0; border-top: 1px solid var(--jf-color-border); }
}

@media (max-width: 480px) {
  .template-workspace__main,
  .template-workspace__side { padding: var(--jf-space-1-5); }
  .template-workspace__state { padding: var(--jf-space-2) var(--jf-space-1-5); }
}
</style>
