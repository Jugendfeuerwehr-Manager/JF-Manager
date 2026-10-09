<template>
  <div class="email-layout-templates">
    <p class="email-layout-templates__intro">Layouts rahmen den Inhalt eigener Vorlagen ein, zum Beispiel mit Kopfzeile und Fußzeile.</p>
    <StateView v-if="loading && !templates.length" kind="loading" />
    <StateView v-else-if="loadState" :kind="loadState" @retry="load" />
    <ul v-else class="layout-list">
      <li v-for="tpl in templates" :key="tpl.layout_type" class="layout-row">
        <button type="button" class="layout-row__main" :aria-label="`${tpl.label} bearbeiten`" @click="handleEdit(tpl.layout_type)">
          <span class="layout-row__icon" aria-hidden="true"><i :class="layoutIcon(tpl.layout_type)"></i></span>
          <span class="layout-row__text">
            <span class="layout-row__title">{{ tpl.label }}</span>
            <span class="layout-row__meta">{{ tpl.updated_at ? `geändert ${formatDate(tpl.updated_at)}` : 'Standardvorlage aus der Installation' }}</span>
          </span>
          <StatusBadge v-if="tpl.is_custom" label="Angepasst" severity="info" icon="pi pi-pencil" />
          <StatusBadge v-else label="Standard" severity="neutral" icon="pi pi-file" />
          <i class="pi pi-chevron-right layout-row__chevron" aria-hidden="true"></i>
        </button>
        <Button
          v-if="tpl.is_custom"
          icon="pi pi-refresh"
          text
          severity="secondary"
          class="layout-row__reset"
          :aria-label="`${tpl.label} auf Standard zurücksetzen`"
          v-tooltip.top="'Auf Standard zurücksetzen'"
          :disabled="saving"
          @click="confirmReset(tpl.layout_type, tpl.label)"
        />
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { format } from 'date-fns'
import Button from 'primevue/button'
import { useEmailLayoutTemplatesStore } from '@/stores/email-layout-templates'
import StateView, { stateForError, type StateKind } from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { classifyApiError } from '@/utils/apiError'

const store = useEmailLayoutTemplatesStore()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()

const loadState = ref<StateKind | null>(null)
const templates = computed(() => store.templates)
const loading = computed(() => store.loading)
const saving = computed(() => store.saving)

async function load() {
  loadState.value = null
  try {
    await store.fetchTemplates()
  } catch (err) {
    loadState.value = stateForError(classifyApiError(err))
  }
}

function handleEdit(layoutType: string) {
  void router.push({ name: 'email-layout-edit', params: { layoutType } })
}

function confirmReset(layoutType: string, label: string) {
  confirm.require({
    message: `Das angepasste Layout „${label}“ wird verworfen und die Standardvorlage wiederhergestellt.`,
    header: 'Layout zurücksetzen?',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Zurücksetzen',
    rejectLabel: 'Abbrechen',
    acceptProps: { severity: 'danger' },
    accept: async () => {
      try {
        await store.resetTemplate(layoutType)
        toast.add({ severity: 'success', summary: 'Zurückgesetzt', detail: 'Standardvorlage wiederhergestellt.', life: 3000 })
      } catch {
        toast.add({ severity: 'error', summary: 'Fehler', detail: 'Layout konnte nicht zurückgesetzt werden.', life: 5000 })
      }
    },
  })
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
  return format(new Date(dateString), 'dd.MM.yyyy')
}

onMounted(() => {
  void load()
})
</script>

<style scoped>
.email-layout-templates {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  padding-top: var(--jf-space-2);
}

.email-layout-templates__intro { margin: 0; font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }

.layout-list {
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  overflow: hidden;
}

.layout-row { display: flex; align-items: center; gap: var(--jf-space-0-5); padding-right: var(--jf-space-1); }
.layout-row + .layout-row { border-top: 1px solid var(--jf-color-border); }

.layout-row__main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  min-height: 64px;
  padding: var(--jf-space-1) var(--jf-space-2);
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.layout-row__main:hover { background: var(--surface-hover); }
.layout-row__main:focus-visible { outline: var(--jf-focus-ring); outline-offset: -2px; }

.layout-row__icon {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-selected);
  color: var(--jf-color-selected-text);
}

.layout-row__text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.layout-row__title { font-weight: var(--jf-weight-semibold); }
.layout-row__meta { font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.layout-row__chevron { color: var(--jf-color-text-muted); font-size: 0.75rem; }
.layout-row__reset { flex-shrink: 0; min-width: var(--jf-touch-target); min-height: var(--jf-touch-target); }

@media (max-width: 480px) {
  .layout-row__main { padding: var(--jf-space-1) var(--jf-space-1-5); gap: var(--jf-space-1); }
  .layout-row__icon, .layout-row__chevron { display: none; }
}
</style>
