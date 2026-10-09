<template>
  <div class="layout-workspace" @keydown="onKeydown">
    <WorkspaceHeader
      :title="layout?.label ?? 'Layout-Vorlage'"
      :back-to="{ name: 'settings-email-templates', query: { tab: 'layouts' } }"
      back-label="E-Mail-Vorlagen"
      eyebrow="Layout"
    >
      <template v-if="layout" #meta>
        <StatusBadge v-if="layout.is_custom" label="Angepasst" severity="info" icon="pi pi-pencil" />
        <StatusBadge v-else label="Standard" severity="neutral" icon="pi pi-file" />
        <span v-if="layout.updated_at">Zuletzt geändert {{ formatDate(layout.updated_at) }}</span>
      </template>
      <template v-if="layout" #status>
        <span class="save-hint" :class="{ 'save-hint--dirty': hasChanges }" role="status">
          <template v-if="saving">Speichert …</template>
          <template v-else-if="hasChanges"><i class="pi pi-pencil" aria-hidden="true"></i>Ungespeicherte Änderungen</template>
          <template v-else><i class="pi pi-check" aria-hidden="true"></i>Alles gespeichert</template>
        </span>
      </template>
      <template v-if="layout" #actions>
        <Button
          v-if="layout.is_custom"
          label="Zurücksetzen"
          icon="pi pi-refresh"
          severity="secondary"
          outlined
          :disabled="saving"
          @click="confirmReset"
        />
        <Button
          label="Speichern"
          icon="pi pi-save"
          :disabled="!hasChanges || saving || !editHtml.trim()"
          :loading="saving"
          v-tooltip.bottom="'Strg + S'"
          @click="handleSave"
        />
      </template>
    </WorkspaceHeader>

    <div v-if="loadState" class="layout-workspace__state">
      <StateView :kind="loadState" :title="loadState === 'empty' ? 'Layout nicht gefunden' : undefined" :message="loadState === 'empty' ? 'Dieses Layout gibt es nicht.' : undefined" @retry="load" />
    </div>

    <div v-else class="layout-workspace__body">
      <section class="layout-workspace__main" aria-labelledby="layout-html-label">
        <div class="layout-workspace__main-head">
          <span id="layout-html-label" class="layout-workspace__label">HTML-Layout</span>
          <p class="layout-workspace__hint">
            <code v-pre>{{ content }}</code> setzt den Inhalt der E-Mail ein, <code v-pre>{{ site_name }}</code> den Anwendungsnamen.
          </p>
        </div>
        <div class="layout-workspace__code">
          <MonacoEditor v-model="editHtml" language="html" height="100%" :theme="isDark ? 'vs-dark' : 'vs'" :minimap="false" wordWrap="on" />
        </div>
      </section>
      <aside class="layout-workspace__side" aria-label="Vorschau">
        <p class="layout-workspace__preview-note">
          <i class="pi pi-info-circle" aria-hidden="true"></i>
          Vereinfachte Vorschau: Platzhalter sind durch Beispieltext ersetzt, Bedingungen ausgeblendet.
        </p>
        <PhoneMockup :subject="`${websiteTitle} – Beispiel`" :htmlContent="previewHtml" />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { format } from 'date-fns'
import Button from 'primevue/button'
import { useEmailLayoutTemplatesStore } from '@/stores/email-layout-templates'
import { useAppSettings } from '@/composables/useAppSettings'
import WorkspaceHeader from '@/components/common/WorkspaceHeader.vue'
import MonacoEditor from '@/components/common/MonacoEditor.vue'
import StateView, { stateForError, type StateKind } from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import PhoneMockup from '../atoms/PhoneMockup.vue'
import { classifyApiError } from '@/utils/apiError'

const props = defineProps<{ layoutType: string }>()

const store = useEmailLayoutTemplatesStore()
const confirm = useConfirm()
const toast = useToast()
const { websiteTitle } = useAppSettings()

const editHtml = ref('')
const loadState = ref<StateKind | null>('loading')

const layout = computed(() => store.templates.find((t) => t.layout_type === props.layoutType) ?? null)
const saving = computed(() => store.saving)
const hasChanges = computed(() => !!layout.value && editHtml.value !== layout.value.html_content)

const SAMPLE_CONTENT = '<h2>Hallo Alex,</h2><p>so erscheint der Inhalt einer E-Mail in diesem Layout. Der eigentliche Text kommt aus der jeweiligen Inhaltsvorlage.</p><p>Viele Grüße<br>Deine Jugendfeuerwehr</p>'

/** Approximates the server rendering for the preview; the server output stays authoritative. */
const previewHtml = computed(() =>
  editHtml.value
    .replace(/\{\{\s*content(\|[^}]*)?\s*\}\}/g, SAMPLE_CONTENT)
    .replace(/\{\{\s*site_name(\|[^}]*)?\s*\}\}/g, websiteTitle.value || 'JF-Manager')
    .replace(/\{%[\s\S]*?%\}/g, '')
    .replace(/\{\{[\s\S]*?\}\}/g, ''),
)

const isDark = ref(document.documentElement.classList.contains('app-dark'))
const themeObserver = new MutationObserver(() => {
  isDark.value = document.documentElement.classList.contains('app-dark')
})

async function load() {
  loadState.value = 'loading'
  try {
    await store.fetchTemplates()
    if (!layout.value) {
      loadState.value = 'empty'
      return
    }
    editHtml.value = layout.value.html_content
    loadState.value = null
  } catch (err) {
    loadState.value = stateForError(classifyApiError(err))
  }
}

async function handleSave() {
  if (!hasChanges.value || saving.value || !editHtml.value.trim()) return
  try {
    await store.updateTemplate(props.layoutType, { html_content: editHtml.value })
    toast.add({ severity: 'success', summary: 'Gespeichert', detail: 'Layout-Vorlage wurde gespeichert.', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Layout-Vorlage konnte nicht gespeichert werden.', life: 5000 })
  }
}

function confirmReset() {
  confirm.require({
    message: 'Das angepasste Layout wird verworfen und die Standardvorlage wiederhergestellt.',
    header: 'Layout zurücksetzen?',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Zurücksetzen',
    rejectLabel: 'Abbrechen',
    acceptProps: { severity: 'danger' },
    accept: async () => {
      try {
        const result = await store.resetTemplate(props.layoutType)
        editHtml.value = result.html_content
        toast.add({ severity: 'success', summary: 'Zurückgesetzt', detail: 'Standardvorlage wiederhergestellt.', life: 3000 })
      } catch {
        toast.add({ severity: 'error', summary: 'Fehler', detail: 'Layout konnte nicht zurückgesetzt werden.', life: 5000 })
      }
    },
  })
}

function onKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    void handleSave()
  }
}

function formatDate(dateString: string): string {
  return format(new Date(dateString), 'dd.MM.yyyy, HH:mm')
}

onBeforeRouteLeave(() => (saving.value ? false : !hasChanges.value || window.confirm('Ungespeicherte Änderungen am Layout verwerfen?')))

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
})
</script>

<style scoped>
.layout-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--jf-color-ground);
}

.layout-workspace__state { flex: 1; padding: var(--jf-space-4) var(--jf-space-3); }

.layout-workspace__body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(340px, 30vw, 440px);
}

.layout-workspace__main {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  min-height: 0;
  padding: var(--jf-space-2) var(--jf-space-3);
  background: var(--jf-color-card);
}

.layout-workspace__label { font-size: var(--jf-text-sm); font-weight: var(--jf-weight-semibold); }
.layout-workspace__hint { margin: 2px 0 0; font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }
.layout-workspace__hint code { font-family: var(--jf-font-mono); }

.layout-workspace__code { flex: 1; min-height: 360px; }
.layout-workspace__code :deep(.monaco-editor-container) { border-color: var(--jf-color-border); border-radius: var(--jf-radius-md); }

.layout-workspace__side {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  min-height: 0;
  overflow-y: auto;
  padding: var(--jf-space-2);
  border-left: 1px solid var(--jf-color-border);
}

.layout-workspace__preview-note {
  display: flex;
  gap: var(--jf-space-0-5);
  margin: 0;
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
}
.layout-workspace__preview-note i { margin-top: 2px; }

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

@media (max-width: 1023px) {
  .layout-workspace { height: auto; }
  .layout-workspace__body { grid-template-columns: minmax(0, 1fr); }
  .layout-workspace__side { overflow: visible; border-left: 0; border-top: 1px solid var(--jf-color-border); }
}

@media (max-width: 480px) {
  .layout-workspace__main, .layout-workspace__side { padding: var(--jf-space-1-5); }
}
</style>
