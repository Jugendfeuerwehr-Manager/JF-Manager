<template>
  <Dialog
    :visible="visible"
    :header="block ? block.title : 'Block bearbeiten'"
    :style="{ width: '900px', maxWidth: 'calc(100vw - 24px)' }"
    modal
    @update:visible="emit('update:visible', $event)"
  >
    <div v-if="block" class="block-edit-layout">
      <!-- Main editor -->
      <div class="edit-main">
        <div class="field mb-3">
          <label for="block-title">Titel</label>
          <InputText id="block-title" v-model="form.title" class="w-full" />
        </div>

        <div class="field-row mb-3">
          <div class="field">
            <label for="block-duration">Dauer (Min.)</label>
            <InputNumber input-id="block-duration" v-model="form.duration_minutes" :min="1" :max="480" class="w-full" />
          </div>
          <div class="field">
            <label for="block-offset">Start-Offset (Min.)</label>
            <InputNumber input-id="block-offset" v-model="form.start_offset_minutes" :min="0" class="w-full" />
          </div>
          <div class="field">
            <label for="block-color">Farbe</label>
            <input id="block-color" type="color" v-model="form.color" class="color-input" />
          </div>
        </div>

        <div class="field mb-3">
          <label for="block-groups">Gruppen (leer = alle Gruppen)</label>
          <MultiSelect input-id="block-groups" v-model="form.group_ids" :options="groupChoices" option-label="name" option-value="id" />
        </div>

        <div class="field mb-3">
          <label for="block-folder">Nextcloud-Ordner-URL</label>
          <InputText id="block-folder" v-model="form.nextcloud_folder_url" class="w-full" placeholder="https://..." />
        </div>

        <div class="field">
          <label>Inhalt</label>
          <BlockEditor
            v-model="form.content"
            block-type="training"
            :block-id="block.id > 0 ? block.id : null"
            min-height="260px"
          />
        </div>
      </div>

      <!-- Asset panel -->
      <div class="edit-panel">
        <AssetPanel v-if="block.id > 0" block-type="training" :block-id="block.id" />
        <p v-else role="status">Speichere den Plan zuerst, um Bilder und Anhänge hinzuzufügen.</p>
      </div>
    </div>

    <template #footer>
      <div class="footer-left">
        <template v-if="isAlreadyInLibrary">
          <Button
            label="Vorlage aktualisieren"
            icon="pi pi-sync"
            severity="secondary"
            outlined
            size="small"
            :loading="savingToLibrary"
            v-tooltip.top="'Bibliotheksvorlage mit aktuellem Inhalt überschreiben'"
            @click="updateLibraryBlock"
          />
          <Button
            label="Als neue Version"
            icon="pi pi-copy"
            severity="secondary"
            outlined
            size="small"
            :loading="savingToLibrary"
            v-tooltip.top="'Neuen Bibliotheksbaustein aus aktuellem Inhalt erstellen'"
            @click="saveToLibrary"
          />
        </template>
        <Button
          v-else
          label="In Bibliothek speichern"
          icon="pi pi-bookmark"
          severity="secondary"
          outlined
          size="small"
          :loading="savingToLibrary"
          @click="saveToLibrary"
        />
      </div>
      <Button label="Abbrechen" severity="secondary" outlined @click="emit('update:visible', false)" />
      <Button label="Übernehmen" icon="pi pi-check" :loading="saving" :disabled="plannerStore.saving" @click="save" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import MultiSelect from 'primevue/multiselect'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import BlockEditor from '../atoms/BlockEditor.vue'
import AssetPanel from './AssetPanel.vue'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'
import { useLibraryStore } from '@/stores/library'
import type { PlannerBlock } from '@/types/training'

interface Props {
  visible: boolean
  block: PlannerBlock | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:visible': [v: boolean]
  saved: [blockId: number]
}>()

const plannerStore = useTrainingPlannerStore()
const libraryStore = useLibraryStore()
const toast = useToast()
const saving = ref(false)
const savingToLibrary = ref(false)

const groupChoices = computed(() => Array.from(new Map([
  ...(plannerStore.session?.groups ?? []), ...plannerStore.blocks.flatMap((b) => b.groups),
].map((g) => [g.id, g])).values()))

const isAlreadyInLibrary = computed(() => props.block?.library_block != null)

const form = ref({
  title: '',
  content: '',
  duration_minutes: 15,
  start_offset_minutes: 0,
  color: '',
  group_ids: [] as number[],
  nextcloud_folder_url: '',
})

watch(() => [props.block, props.visible] as const, ([b, visible]) => {
  if (b && visible) {
    form.value = {
      title: b.title,
      content: b.content ?? '',
      duration_minutes: b.duration_minutes,
      start_offset_minutes: b.start_offset_minutes ?? 0,
      color: b.color ?? '',
      group_ids: [...b.groupIds],
      nextcloud_folder_url: b.nextcloud_folder_url ?? '',
    }
  }
}, { immediate: true })

async function save() {
  if (!props.block) return
  saving.value = true
  try {
    await plannerStore.updateBlockContent(props.block.id, form.value)
    emit('saved', props.block.id)
    emit('update:visible', false)
  } catch {
    toast.add({ severity: 'error', summary: 'Nicht übernommen', detail: 'Bitte warte, bis der Plan gespeichert ist.', life: 4000 })
  } finally {
    saving.value = false
  }
}

async function saveToLibrary() {
  if (!props.block) return
  savingToLibrary.value = true
  try {
    await libraryStore.createBlock({
      title: form.value.title,
      content: form.value.content || undefined,
      default_duration_minutes: form.value.duration_minutes,
      color: form.value.color || undefined,
      nextcloud_folder_url: form.value.nextcloud_folder_url || undefined,
    })
    toast.add({ severity: 'success', summary: 'In Bibliothek gespeichert', detail: `"${form.value.title}" wurde zur Bibliothek hinzugefügt.`, life: 3500 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Baustein konnte nicht in die Bibliothek gespeichert werden.', life: 4000 })
  } finally {
    savingToLibrary.value = false
  }
}

async function updateLibraryBlock() {
  if (!props.block?.library_block) return
  savingToLibrary.value = true
  try {
    await libraryStore.updateBlock(props.block.library_block, {
      title: form.value.title,
      content: form.value.content || undefined,
      default_duration_minutes: form.value.duration_minutes,
      color: form.value.color || undefined,
      nextcloud_folder_url: form.value.nextcloud_folder_url || undefined,
    })
    toast.add({ severity: 'success', summary: 'Vorlage aktualisiert', detail: `"${form.value.title}" wurde in der Bibliothek aktualisiert.`, life: 3500 })
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Vorlage konnte nicht aktualisiert werden.', life: 4000 })
  } finally {
    savingToLibrary.value = false
  }
}
</script>

<style scoped>
.block-edit-layout {
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: 1rem;
}
.edit-main { display: flex; flex-direction: column; gap: 0.75rem; }
.edit-panel { }

.field { display: flex; flex-direction: column; gap: 0.35rem; }
.field label { font-size: 0.875rem; font-weight: 500; color: var(--text-color-secondary); }
.field-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; }

.color-input { width: 2.5rem; height: 2rem; border: none; background: none; cursor: pointer; }

.footer-left { flex: 1; display: flex; align-items: center; gap: 0.5rem; }
</style>

<style scoped>
@media (max-width: 640px) { .block-edit-layout { grid-template-columns: 1fr; } .edit-panel { width: 100%; border-left: 0; } .field-row { grid-template-columns: 1fr; } }
</style>
