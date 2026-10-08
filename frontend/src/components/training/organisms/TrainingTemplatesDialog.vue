<template>
  <Dialog :visible="visible" header="Übungsvorlagen" modal :style="{ width: '760px', maxWidth: 'calc(100vw - 24px)' }" @update:visible="emit('update:visible', $event)">
    <div class="templates">
      <p>
        Eine neue Übung aus einer Vorlage ist ein eigenständiger Entwurf mit eigenen Bild- und Anhangkopien. Vorlagen
        entstehen im Planer über „Weitere Aktionen → Als Vorlage speichern“.
      </p>
      <div class="templates__toolbar">
        <label for="template-date">Datum der neuen Übung</label>
        <InputText id="template-date" v-model="date" type="date" />
        <InputText v-model="search" placeholder="Vorlagen suchen…" aria-label="Vorlagen suchen" />
      </div>
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
      <div v-if="loading" role="status">Vorlagen laden …</div>
      <p v-else-if="!filtered.length" class="templates__empty">Keine Vorlagen gefunden.</p>
      <ul v-else class="templates__list">
        <li v-for="template in filtered" :key="template.id" class="templates__item">
          <div class="templates__info">
            <strong>{{ template.title }}</strong>
            <span class="templates__meta">
              {{ template.start_time.slice(0, 5) }}–{{ template.end_time.slice(0, 5) }} ·
              {{ template.block_count }} Bausteine<template v-if="template.location"> · {{ template.location }}</template>
            </span>
            <span v-if="template.description" class="templates__meta">{{ template.description }}</span>
          </div>
          <div class="templates__actions">
            <Button label="Übung anlegen" icon="pi pi-plus" size="small" :disabled="!date || busyId !== null" :loading="busyId === template.id" @click="instantiate(template)" />
            <Button icon="pi pi-trash" text severity="danger" size="small" :aria-label="`Vorlage ${template.title} löschen`" :disabled="busyId !== null" @click="remove(template)" />
          </div>
        </li>
      </ul>
    </div>
    <template #footer>
      <Button label="Schließen" severity="secondary" @click="emit('update:visible', false)" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { trainingTemplatesApi } from '@/api/training'
import type { TrainingSessionDetail, TrainingTemplate } from '@/types/training'

const props = defineProps<{ visible: boolean; defaultDate?: string | null; department?: number | null }>()
const emit = defineEmits<{ 'update:visible': [visible: boolean]; created: [session: TrainingSessionDetail] }>()

const templates = ref<TrainingTemplate[]>([])
const date = ref('')
const search = ref('')
const loading = ref(false)
const busyId = ref<number | null>(null)
const error = ref('')

const filtered = computed(() => {
  const query = search.value.trim().toLowerCase()
  if (!query) return templates.value
  return templates.value.filter((t) => `${t.title} ${t.description} ${t.location}`.toLowerCase().includes(query))
})

function messages(value: unknown): string[] {
  if (typeof value === 'string') return [value]
  if (value && typeof value === 'object') return Object.values(value).flatMap(messages)
  return []
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, unknown> = { limit: 500 }
    if (props.department) params.department = props.department
    templates.value = (await trainingTemplatesApi.list(params)).data.results
  } catch (e: unknown) {
    const data = (e as { response?: { data?: unknown } }).response?.data
    error.value = messages(data).join(' ') || 'Vorlagen konnten nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

async function instantiate(template: TrainingTemplate) {
  if (!date.value) return
  busyId.value = template.id
  error.value = ''
  try {
    const { data } = await trainingTemplatesApi.instantiate(template.id, { date: date.value })
    emit('created', data)
    emit('update:visible', false)
  } catch (e: unknown) {
    const data = (e as { response?: { data?: unknown } }).response?.data
    error.value = messages(data).join(' ') || 'Übung wurde nicht angelegt. Verbindung und Berechtigung prüfen.'
  } finally {
    busyId.value = null
  }
}

async function remove(template: TrainingTemplate) {
  if (!window.confirm(`Vorlage „${template.title}“ löschen? Bereits erstellte Übungen bleiben unverändert.`)) return
  busyId.value = template.id
  error.value = ''
  try {
    await trainingTemplatesApi.delete(template.id)
    templates.value = templates.value.filter((t) => t.id !== template.id)
  } catch (e: unknown) {
    const data = (e as { response?: { data?: unknown } }).response?.data
    error.value = messages(data).join(' ') || 'Vorlage wurde nicht gelöscht.'
  } finally {
    busyId.value = null
  }
}

watch(
  () => props.visible,
  (visible) => {
    if (!visible) return
    date.value = props.defaultDate ?? ''
    search.value = ''
    void load()
  },
  { immediate: true },
)
</script>

<style scoped>
.templates { display: grid; gap: var(--jf-space-2); }
.templates p { margin: 0; }
.templates__toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-2); }
.templates__toolbar label { font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.templates__empty { color: var(--jf-color-text-muted); }
.templates__list { display: grid; gap: var(--jf-space-1); margin: 0; padding: 0; list-style: none; max-height: 55vh; overflow: auto; }
.templates__item { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: var(--jf-space-2); padding: var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); }
.templates__info { display: grid; gap: var(--jf-space-0-5); min-width: 0; }
.templates__meta { font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.templates__actions { display: flex; gap: var(--jf-space-1); }
</style>
