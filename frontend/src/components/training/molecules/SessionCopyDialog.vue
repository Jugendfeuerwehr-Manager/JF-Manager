<template>
  <Dialog :visible="visible" :header="mode === 'copy' ? 'Übung kopieren' : 'Als Vorlage speichern'" modal :style="{ width: '520px', maxWidth: 'calc(100vw - 24px)' }" @update:visible="emit('update:visible', $event)">
    <form class="copy-dialog" @submit.prevent="submit">
      <p v-if="mode === 'copy'">
        Es entsteht ein eigenständiger Entwurf mit dem gespeicherten Ablauf, eigenen Bild- und Anhangkopien und ohne
        Dienst. Spätere Änderungen an dieser Übung wirken sich nicht auf die Kopie aus.
      </p>
      <p v-else>
        Die Vorlage enthält den gespeicherten Ablauf mit eigenen Bild- und Anhangkopien. Spätere Änderungen oder das
        Löschen dieser Übung ändern die Vorlage nicht.
      </p>
      <label for="copy-title">{{ mode === 'copy' ? 'Titel der Kopie' : 'Name der Vorlage' }}</label>
      <InputText id="copy-title" v-model="title" maxlength="300" />
      <template v-if="mode === 'copy'">
        <label for="copy-date">Datum</label>
        <InputText id="copy-date" v-model="date" type="date" required />
      </template>
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
      <div class="copy-dialog__actions">
        <Button type="button" label="Abbrechen" severity="secondary" @click="emit('update:visible', false)" />
        <Button type="submit" :label="mode === 'copy' ? 'Kopie anlegen' : 'Vorlage speichern'" icon="pi pi-check" :loading="saving" :disabled="saving || (mode === 'copy' && !date)" />
      </div>
    </form>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { trainingSessionsApi } from '@/api/training'
import type { TrainingSessionDetail, TrainingTemplate } from '@/types/training'

const props = defineProps<{
  visible: boolean
  mode: 'copy' | 'template'
  session: Pick<TrainingSessionDetail, 'id' | 'title' | 'date'> | null
}>()
const emit = defineEmits<{
  'update:visible': [visible: boolean]
  copied: [session: TrainingSessionDetail]
  saved: [template: TrainingTemplate]
}>()

const title = ref('')
const date = ref('')
const saving = ref(false)
const error = ref('')

watch(
  () => props.visible,
  (visible) => {
    if (!visible || !props.session) return
    title.value = props.session.title
    date.value = ''
    error.value = ''
  },
  { immediate: true },
)

function messages(value: unknown): string[] {
  if (typeof value === 'string') return [value]
  if (value && typeof value === 'object') return Object.values(value).flatMap(messages)
  return []
}

async function submit() {
  if (!props.session || saving.value) return
  saving.value = true
  error.value = ''
  try {
    if (props.mode === 'copy') {
      const { data } = await trainingSessionsApi.copy(props.session.id, { date: date.value, title: title.value.trim() })
      emit('copied', data)
    } else {
      const { data } = await trainingSessionsApi.saveAsTemplate(props.session.id, { title: title.value.trim() })
      emit('saved', data)
    }
    emit('update:visible', false)
  } catch (e: unknown) {
    const data = (e as { response?: { data?: unknown } }).response?.data
    error.value = messages(data).join(' ') || 'Nicht gespeichert. Verbindung und Berechtigung prüfen und erneut versuchen.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.copy-dialog { display: grid; gap: var(--jf-space-2); }
.copy-dialog p { margin: 0; }
.copy-dialog label { font-size: var(--jf-text-sm); font-weight: var(--jf-weight-medium); color: var(--jf-color-text-muted); }
.copy-dialog__actions { display: flex; justify-content: flex-end; gap: var(--jf-space-2); padding-top: var(--jf-space-2); }
</style>
