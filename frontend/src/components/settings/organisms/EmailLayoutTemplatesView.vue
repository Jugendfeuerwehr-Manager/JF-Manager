<template>
  <div class="email-layout-templates">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state">
      <Message severity="error">{{ error }}</Message>
    </div>

    <!-- Editor view -->
    <div v-else-if="editingLayout" class="editor-view">
      <div class="editor-header">
        <div class="editor-header__left">
          <Button
            icon="pi pi-arrow-left"
            text
            label="Zurück"
            @click="handleBack"
          />
          <h3>{{ editingLayout.label }}</h3>
          <Tag v-if="editingLayout.is_custom" value="Angepasst" severity="warn" />
          <Tag v-else value="Standard" severity="secondary" />
        </div>
        <div class="editor-header__actions">
          <Button
            v-if="editingLayout.is_custom"
            label="Zurücksetzen"
            icon="pi pi-refresh"
            severity="secondary"
            outlined
            :loading="saving"
            @click="handleReset"
          />
          <Button
            label="Speichern"
            icon="pi pi-save"
            :loading="saving"
            :disabled="!hasChanges"
            @click="handleSave"
          />
        </div>
      </div>

      <div class="editor-body">
        <Card>
          <template #title>HTML-Layout bearbeiten</template>
          <template #subtitle>
            Verwende <code v-pre>{{ content }}</code> als Platzhalter für den E-Mail-Inhalt und
            <code v-pre>{{ site_name }}</code> für den Anwendungsnamen.
          </template>
          <template #content>
            <Textarea
              v-model="editHtml"
              rows="30"
              class="html-editor"
              :auto-resize="false"
            />
          </template>
        </Card>
      </div>
    </div>

    <!-- List view -->
    <div v-else class="list-view">
      <div class="layout-cards">
        <Card v-for="tpl in templates" :key="tpl.layout_type" class="layout-card">
          <template #header>
            <div class="layout-card__header">
              <span class="layout-card__icon">
                <i :class="layoutIcon(tpl.layout_type)" />
              </span>
            </div>
          </template>
          <template #title>{{ tpl.label }}</template>
          <template #subtitle>
            <Tag v-if="tpl.is_custom" value="Angepasst" severity="warn" />
            <Tag v-else value="Standard (Datei)" severity="secondary" />
          </template>
          <template #content>
            <p v-if="tpl.updated_at" class="layout-card__date">
              Zuletzt geändert: {{ formatDate(tpl.updated_at) }}
            </p>
          </template>
          <template #footer>
            <div class="layout-card__actions">
              <Button
                label="Bearbeiten"
                icon="pi pi-pencil"
                size="small"
                @click="handleEdit(tpl)"
              />
              <Button
                v-if="tpl.is_custom"
                label="Zurücksetzen"
                icon="pi pi-refresh"
                size="small"
                severity="secondary"
                outlined
                :loading="saving"
                @click="handleResetFromList(tpl.layout_type)"
              />
            </div>
          </template>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useEmailLayoutTemplatesStore } from '@/stores/email-layout-templates'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { format } from 'date-fns'
import type { EmailLayoutTemplate } from '@/types/email-layout-templates'

const store = useEmailLayoutTemplatesStore()
const toast = useToast()

const editingLayout = ref<EmailLayoutTemplate | null>(null)
const editHtml = ref('')

const templates = computed(() => store.templates)
const loading = computed(() => store.loading)
const saving = computed(() => store.saving)
const error = computed(() => store.error)

const hasChanges = computed(() => {
  if (!editingLayout.value) return false
  return editHtml.value !== editingLayout.value.html_content
})

onMounted(() => store.fetchTemplates())

function handleEdit(tpl: EmailLayoutTemplate) {
  editingLayout.value = { ...tpl }
  editHtml.value = tpl.html_content
}

function handleBack() {
  editingLayout.value = null
  editHtml.value = ''
}

async function handleSave() {
  if (!editingLayout.value) return
  try {
    await store.updateTemplate(editingLayout.value.layout_type, { html_content: editHtml.value })
    // Refresh the in-memory copy so hasChanges stays accurate
    const updated = templates.value.find((t) => t.layout_type === editingLayout.value!.layout_type)
    if (updated) editingLayout.value = { ...updated }
    toast.add({ severity: 'success', summary: 'Gespeichert', detail: 'Layout-Vorlage wurde gespeichert.', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Konnte nicht gespeichert werden.', life: 5000 })
  }
}

async function handleReset() {
  if (!editingLayout.value) return
  try {
    const result = await store.resetTemplate(editingLayout.value.layout_type)
    editingLayout.value = { ...result }
    editHtml.value = result.html_content
    toast.add({ severity: 'success', summary: 'Zurückgesetzt', detail: 'Standardvorlage wiederhergestellt.', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Konnte nicht zurückgesetzt werden.', life: 5000 })
  }
}

async function handleResetFromList(layoutType: string) {
  try {
    await store.resetTemplate(layoutType)
    toast.add({ severity: 'success', summary: 'Zurückgesetzt', detail: 'Standardvorlage wiederhergestellt.', life: 3000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Konnte nicht zurückgesetzt werden.', life: 5000 })
  }
}

function layoutIcon(layoutType: string): string {
  switch (layoutType) {
    case 'general': return 'pi pi-envelope'
    case 'important': return 'pi pi-exclamation-triangle'
    case 'events': return 'pi pi-calendar'
    default: return 'pi pi-file'
  }
}

function formatDate(dateString: string): string {
  return format(new Date(dateString), 'dd.MM.yyyy HH:mm')
}
</script>

<style scoped>
.loading-state,
.error-state {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.editor-header__left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.editor-header__left h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
}

.editor-header__actions {
  display: flex;
  gap: 0.5rem;
}

.html-editor {
  width: 100%;
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  resize: vertical;
}

.layout-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.layout-card__header {
  display: flex;
  justify-content: center;
  padding: 1.5rem 0 0.5rem;
  font-size: 2rem;
  color: var(--p-primary-color);
}

.layout-card__date {
  margin: 0;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

.layout-card__actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
</style>
