<template>
  <div class="library-block-form">
    <div class="form-layout" :class="{ 'with-panel': showAssetPanel }">
      <!-- Main form fields -->
      <div class="form-main">
        <div class="field">
          <label for="lb-title">Titel *</label>
          <InputText id="lb-title" v-model="form.title" :invalid="!form.title && submitted" class="w-full" />
          <small v-if="!form.title && submitted" class="p-error">Bitte Titel eingeben</small>
        </div>

        <div class="field">
          <label for="lb-description">Kurzbeschreibung</label>
          <Textarea id="lb-description" v-model="form.description" rows="2" class="w-full" />
        </div>

        <div class="field-row">
          <div class="field">
            <label>Kategorie</label>
            <Select
              v-model="form.category_id"
              :options="categories"
              option-label="name"
              option-value="id"
              show-clear
              placeholder="Keine Kategorie"
              class="w-full"
            />
          </div>

          <div class="field">
            <label>Dauer (Min.)</label>
            <InputNumber v-model="form.default_duration_minutes" :min="1" :max="480" class="w-full" />
          </div>

          <div class="field">
            <label>Farbe</label>
            <div class="color-picker-row">
              <input type="color" v-model="form.color" class="color-input" />
              <span class="color-hint">{{ form.color ?? 'Keine' }}</span>
            </div>
          </div>
        </div>

        <div class="field">
          <label>Tags</label>
          <MultiSelect
            v-model="form.tag_ids"
            :options="tags"
            option-label="name"
            option-value="id"
            placeholder="Tags auswählen"
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Nextcloud-Ordner-URL</label>
          <InputText v-model="form.nextcloud_folder_url" class="w-full" placeholder="https://…" />
        </div>

        <div class="field field-checkbox">
          <Checkbox v-model="form.is_public" input-id="lb-public" :binary="true" />
          <label for="lb-public">Öffentlich (für Export freigeben)</label>
        </div>

        <div class="field">
          <label>Inhalt</label>
          <div class="editor-wrapper">
            <BlockEditor
              v-model="form.content"
              :block-type="blockType"
              :block-id="currentBlockId"
              placeholder="Ausbildungsinhalt hier beschreiben…"
              min-height="300px"
            />
          </div>
        </div>
      </div>

      <!-- Asset panel (shown when blockId exists) -->
      <div v-if="showAssetPanel" class="form-panel">
        <AssetPanel :block-type="blockType" :block-id="currentBlockId" />
      </div>
    </div>

    <div class="form-actions">
      <Button label="Abbrechen" severity="secondary" outlined @click="emit('cancel')" />
      <Button
        :label="initialData ? 'Speichern' : 'Erstellen'"
        icon="pi pi-check"
        :loading="saving"
        @click="submit"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import BlockEditor from '../atoms/BlockEditor.vue'
import AssetPanel from './AssetPanel.vue'
import { useLibraryStore } from '@/stores/library'
import { useToast } from 'primevue/usetoast'
import { storeToRefs } from 'pinia'
import type { LibraryBlockDetail, LibraryBlockCreate } from '@/types/training'

/** Internal form state - all fields required to avoid undefined assignment errors */
interface BlockFormData {
  title: string
  description: string
  content: string
  default_duration_minutes: number
  category_id: number | null
  tag_ids: number[]
  color: string
  nextcloud_folder_url: string
  is_public: boolean
}

interface Props {
  initialData?: LibraryBlockDetail | null
  blockType?: 'library' | 'training'
}

const props = withDefaults(defineProps<Props>(), { blockType: 'library' })
const emit = defineEmits<{
  success: [blockId: number]
  cancel: []
}>()

const libraryStore = useLibraryStore()
const { categories, tags, saving } = storeToRefs(libraryStore)
const toast = useToast()
const submitted = ref(false)
const currentBlockId = ref<number | null>(props.initialData?.id ?? null)

const form = ref<BlockFormData>({
  title: '',
  description: '',
  content: '',
  default_duration_minutes: 15,
  category_id: null,
  tag_ids: [],
  color: '',
  nextcloud_folder_url: '',
  is_public: false,
})

const showAssetPanel = computed(() => currentBlockId.value !== null)

onMounted(async () => {
  await Promise.all([libraryStore.fetchCategories(), libraryStore.fetchTags()])
  if (props.initialData) populateForm(props.initialData)
})

watch(() => props.initialData, (data) => {
  if (data) {
    populateForm(data)
    currentBlockId.value = data.id
  }
})

function populateForm(data: LibraryBlockDetail) {
  form.value = {
    title: data.title,
    description: data.description ?? '',
    content: data.content ?? '',
    default_duration_minutes: data.default_duration_minutes ?? 15,
    category_id: data.category?.id ?? null,
    tag_ids: data.tags.map((t) => t.id),
    color: data.color ?? '',
    nextcloud_folder_url: data.nextcloud_folder_url ?? '',
    is_public: data.is_public,
  }
}

async function submit() {
  submitted.value = true
  if (!form.value.title.trim()) return

  try {
    if (props.initialData) {
      await libraryStore.updateBlock(props.initialData.id, form.value as LibraryBlockCreate)
      emit('success', props.initialData.id)
    } else {
      const block = await libraryStore.createBlock(form.value as LibraryBlockCreate)
      if (block) {
        currentBlockId.value = block.id
        emit('success', block.id)
      }
    }
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler beim Speichern',
      detail: libraryStore.error ?? 'Bitte überprüfe deine Eingaben und versuche es erneut.',
      life: 6000,
    })
  }
}
</script>

<style scoped>
.form-layout {
  display: flex;
  gap: 1rem;
}
.form-layout.with-panel {
  grid-template-columns: 1fr 280px;
  display: grid;
}
.form-main { flex: 1; display: flex; flex-direction: column; gap: 1rem; }
.form-panel { width: 280px; flex-shrink: 0; }

.field { display: flex; flex-direction: column; gap: 0.35rem; }
.field-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; }
.field-checkbox { flex-direction: row; align-items: center; gap: 0.5rem; }
.field label { font-size: 0.875rem; font-weight: 500; color: var(--p-text-muted-color); }

.color-picker-row { display: flex; align-items: center; gap: 0.5rem; }
.color-input { width: 2.5rem; height: 2rem; border: none; background: none; cursor: pointer; }
.color-hint { font-size: 0.875rem; color: var(--p-text-muted-color); }

.editor-wrapper { min-height: 0; }

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--p-content-border-color);
  margin-top: 1rem;
}
</style>
