<template>
  <div class="email-templates-view">
    <div class="email-templates-view__toolbar">
      <p class="email-templates-view__intro">Eigene Vorlagen ersetzen die Standard-E-Mail ihres Typs. Der Editor öffnet sich als Arbeitsfläche mit Live-Vorschau.</p>
      <Button
        label="Neue Vorlage"
        icon="pi pi-plus"
        :disabled="!hasAvailableTypes"
        v-tooltip.bottom="hasAvailableTypes ? undefined : 'Für alle Typen gibt es bereits eine Vorlage'"
        @click="handleCreate"
      />
    </div>

    <StateView v-if="loading && !templates.length" kind="loading" />
    <StateView v-else-if="loadState" :kind="loadState" @retry="loadInitialData" />
    <EmailTemplatesList
      v-else
      :templates="templates"
      :can-create="hasAvailableTypes"
      @edit="handleEdit"
      @delete="handleDeleteConfirm"
      @create="handleCreate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import { useEmailTemplatesStore } from '@/stores/email-templates'
import StateView, { stateForError, type StateKind } from '@/components/common/StateView.vue'
import EmailTemplatesList from '../molecules/EmailTemplatesList.vue'
import { classifyApiError } from '@/utils/apiError'

const store = useEmailTemplatesStore()
const router = useRouter()
const confirm = useConfirm()
const toast = useToast()

const loadState = ref<StateKind | null>(null)
const templates = computed(() => store.templates)
const loading = computed(() => store.loading)

const hasAvailableTypes = computed(() => {
  const usedTypes = new Set(templates.value.map((t) => t.template_type))
  return store.templateTypes.some((t) => !usedTypes.has(t.value))
})

async function loadInitialData() {
  loadState.value = null
  try {
    await Promise.all([store.fetchTemplates(), store.fetchTemplateTypes()])
  } catch (err) {
    loadState.value = stateForError(classifyApiError(err))
  }
}

function handleEdit(id: number) {
  void router.push({ name: 'email-template-edit', params: { id } })
}

function handleCreate() {
  void router.push({ name: 'email-template-new' })
}

function handleDeleteConfirm(id: number) {
  confirm.require({
    message: 'Die Vorlage wird gelöscht; E-Mails dieses Typs nutzen danach wieder die Standardvorlage.',
    header: 'Vorlage löschen?',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptProps: { severity: 'danger' },
    accept: async () => {
      try {
        await store.deleteTemplate(id)
        toast.add({ severity: 'success', summary: 'Gelöscht', detail: 'Vorlage wurde gelöscht.', life: 3000 })
      } catch {
        toast.add({ severity: 'error', summary: 'Fehler', detail: 'Vorlage konnte nicht gelöscht werden.', life: 5000 })
      }
    },
  })
}

onMounted(() => {
  void loadInitialData()
})
</script>

<style scoped>
.email-templates-view {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  padding-top: var(--jf-space-2);
}

.email-templates-view__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1-5);
}

.email-templates-view__intro {
  flex: 1 1 20rem;
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}
</style>
