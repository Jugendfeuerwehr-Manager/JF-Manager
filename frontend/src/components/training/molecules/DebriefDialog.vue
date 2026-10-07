<template>
  <Dialog
    :visible="visible"
    header="Nachbereitung"
    modal
    :style="{ width: '640px', maxWidth: 'calc(100vw - 24px)' }"
    @update:visible="emit('update:visible', $event)"
  >
    <p v-if="loading" role="status">Wird geladen …</p>
    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>
    <form v-else class="debrief" @submit.prevent="save()">
      <p class="debrief__muted">
        Anwesenheiten werden im Dienstbuch erfasst. Die Planzeit bleibt unverändert; hier steht, wie es tatsächlich lief.
      </p>

      <fieldset class="debrief__times">
        <legend>Tatsächliche Zeit</legend>
        <div class="field">
          <label for="debrief-start">Beginn</label>
          <input id="debrief-start" v-model="form.actual_start" type="time" class="p-inputtext" />
        </div>
        <div class="field">
          <label for="debrief-end">Ende</label>
          <input id="debrief-end" v-model="form.actual_end" type="time" class="p-inputtext" />
        </div>
        <Button label="Planzeit übernehmen" text size="small" type="button" @click="usePlanTime" />
        <p class="debrief__compare" role="status">
          Geplant {{ plannedLabel }} ({{ planned }} Min.)<template v-if="actualMinutes !== null"> · tatsächlich {{ actualMinutes }} Min.<template v-if="actualMinutes !== planned"> ({{ actualMinutes > planned ? '+' : '' }}{{ actualMinutes - planned }})</template></template>
        </p>
      </fieldset>

      <div class="field">
        <label for="debrief-reflection">Reflexion</label>
        <Textarea id="debrief-reflection" v-model="form.reflection" rows="3" auto-resize maxlength="5000" placeholder="Was lief gut, was nicht?" />
      </div>
      <div class="field">
        <label for="debrief-improvements">Verbesserungshinweise</label>
        <Textarea id="debrief-improvements" v-model="form.improvements" rows="3" auto-resize maxlength="5000" placeholder="Was ändern wir beim nächsten Mal?" />
      </div>

      <div v-if="canComplete" class="debrief__complete">
        <Checkbox v-model="form.complete" input-id="debrief-complete" binary />
        <label for="debrief-complete">Übung zugleich abschließen (Anwesenheiten im Dienstbuch bleiben erhalten)</label>
      </div>

      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
      <div v-if="conflict" class="debrief__conflict" role="alert">
        <p>
          <strong>Inzwischen geändert</strong>{{ conflict.updated_by_name ? ` von ${conflict.updated_by_name}` : '' }}.
          Deine Eingaben sind noch hier. Gespeichert ist:
        </p>
        <ul>
          <li>Zeit: {{ conflict.actual_start ? `${short(conflict.actual_start)}–${short(conflict.actual_end)}` : 'keine' }}</li>
          <li>Reflexion: {{ conflict.reflection || '–' }}</li>
          <li>Verbesserungshinweise: {{ conflict.improvements || '–' }}</li>
        </ul>
        <div class="debrief__conflict-actions">
          <Button label="Gespeicherten Stand laden" severity="secondary" size="small" type="button" @click="adopt(conflict)" />
          <Button label="Meine Eingaben speichern" size="small" type="button" @click="save(conflict.revision)" />
        </div>
      </div>
    </form>
    <template #footer>
      <Button label="Abbrechen" severity="secondary" @click="emit('update:visible', false)" />
      <Button label="Speichern" icon="pi pi-check" :loading="saving" :disabled="loading || !!loadError" @click="save()" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'
import { trainingSessionsApi } from '@/api/training'
import type { TrainingDebrief, TrainingStatus } from '@/types/training'

const props = defineProps<{
  visible: boolean
  session: { id: number; status: TrainingStatus; start_time: string; end_time: string; linked_service_id: number | null }
}>()
const emit = defineEmits<{ 'update:visible': [visible: boolean]; saved: [debrief: TrainingDebrief] }>()

const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const error = ref('')
const conflict = ref<TrainingDebrief | null>(null)
const revision = ref(0)
const form = ref({ actual_start: '', actual_end: '', reflection: '', improvements: '', complete: false })

const short = (value: string | null) => (value ?? '').slice(0, 5)
const toMinutes = (value: string) => {
  const [h, m] = value.split(':').map(Number)
  return (h ?? 0) * 60 + (m ?? 0)
}
const planned = computed(() => toMinutes(props.session.end_time) - toMinutes(props.session.start_time))
const plannedLabel = computed(() => `${short(props.session.start_time)}–${short(props.session.end_time)}`)
const actualMinutes = computed(() =>
  form.value.actual_start && form.value.actual_end ? toMinutes(form.value.actual_end) - toMinutes(form.value.actual_start) : null,
)
const canComplete = computed(() => props.session.status === 'published' && props.session.linked_service_id !== null)

function adopt(data: TrainingDebrief) {
  revision.value = data.revision
  form.value = {
    actual_start: short(data.actual_start), actual_end: short(data.actual_end),
    reflection: data.reflection, improvements: data.improvements, complete: false,
  }
  conflict.value = null
}

function usePlanTime() {
  form.value.actual_start = short(props.session.start_time)
  form.value.actual_end = short(props.session.end_time)
}

async function load() {
  loading.value = true
  loadError.value = ''
  error.value = ''
  conflict.value = null
  try {
    adopt((await trainingSessionsApi.debrief(props.session.id)).data)
  } catch {
    loadError.value = 'Die Nachbereitung konnte nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

async function save(expected = revision.value) {
  if (saving.value) return
  error.value = ''
  if (Boolean(form.value.actual_start) !== Boolean(form.value.actual_end)) {
    error.value = 'Tatsächlichen Beginn und Ende gemeinsam angeben.'
    return
  }
  if (actualMinutes.value !== null && actualMinutes.value <= 0) {
    error.value = 'Das tatsächliche Ende muss nach dem Beginn liegen.'
    return
  }
  saving.value = true
  try {
    const { data } = await trainingSessionsApi.saveDebrief(props.session.id, {
      expected_revision: expected,
      actual_start: form.value.actual_start || null,
      actual_end: form.value.actual_end || null,
      reflection: form.value.reflection,
      improvements: form.value.improvements,
      complete: canComplete.value && form.value.complete,
    })
    revision.value = data.revision
    conflict.value = null
    emit('saved', data)
    emit('update:visible', false)
  } catch (e) {
    const response = (e as { response?: { status: number; data?: Record<string, unknown> & { current?: TrainingDebrief } } }).response
    if (response?.status === 409 && response.data?.current) {
      conflict.value = response.data.current
    } else {
      const detail = response?.data && typeof response.data === 'object' ? Object.values(response.data).flat()[0] : null
      error.value = typeof detail === 'string' ? detail : 'Speichern fehlgeschlagen. Eingaben bleiben erhalten.'
    }
  } finally {
    saving.value = false
  }
}

watch(() => props.visible, (open) => { if (open) void load() }, { immediate: true })
</script>

<style scoped>
.debrief { display: flex; flex-direction: column; gap: var(--jf-space-2); }
.debrief p { margin: 0; }
.debrief__muted { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.debrief__times { display: flex; flex-wrap: wrap; align-items: flex-end; gap: var(--jf-space-1) var(--jf-space-2); margin: 0; padding: var(--jf-space-1-5) var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); }
.debrief__times legend { padding: 0 var(--jf-space-0-5); font-weight: var(--jf-weight-semibold); }
.debrief__compare { flex-basis: 100%; font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.field { display: flex; flex-direction: column; gap: 0.35rem; min-width: 0; }
.field label { font-size: var(--jf-text-sm); font-weight: var(--jf-weight-medium); color: var(--jf-color-text-muted); }
.field input[type='time'] { min-height: var(--jf-touch-target); }
.debrief__complete { display: flex; align-items: center; gap: var(--jf-space-1); min-height: var(--jf-touch-target); }
.debrief__conflict { padding: var(--jf-space-1-5) var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); background: var(--jf-color-ground); font-size: var(--jf-text-sm); }
.debrief__conflict ul { margin: var(--jf-space-1) 0; padding-left: 1.1rem; }
.debrief__conflict-actions { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); }
</style>
