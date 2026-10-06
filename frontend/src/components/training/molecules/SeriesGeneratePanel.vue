<template>
  <div class="series-panel">
    <p>
      Fehlende Termine werden als eigenständige Entwürfe mit dem aktuell gespeicherten Ablauf angelegt.
      Vorhandene Termine, Pläne, Dienste und Anwesenheiten bleiben unverändert.
    </p>
    <form class="series-panel__window" @submit.prevent="load">
      <label for="series-window-start">Von</label>
      <InputText id="series-window-start" v-model="windowStart" type="date" />
      <label for="series-window-end">Bis (höchstens 24 Monate)</label>
      <InputText id="series-window-end" v-model="windowEnd" type="date" />
      <Button type="submit" label="Vorschau aktualisieren" severity="secondary" :loading="loading" />
    </form>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Message v-if="notice" severity="success" :closable="false">{{ notice }}</Message>
    <div v-if="loading && !preview" role="status">Vorschau lädt …</div>
    <template v-else-if="preview">
      <div class="series-panel__bar">
        <p class="series-panel__summary" role="status">
          {{ preview.counts.new }} neu · {{ preview.counts.preserved }} vorhanden ·
          {{ preview.counts.skipped }} ausgelassen · {{ preview.counts.conflict }} Konflikte
          <span class="series-panel__muted">({{ formatDate(preview.window_start) }} – {{ formatDate(preview.window_end) }}, {{ frequencyLabel }})</span>
        </p>
        <div class="series-panel__actions">
          <Button
            :label="preview?.counts.new ? `${preview.counts.new} Termine anlegen` : 'Keine neuen Termine'"
            icon="pi pi-check"
            :disabled="!preview || !preview.counts.new || loading || saving"
            :loading="saving"
            @click="generate"
          />
        </div>
      </div>
      <div class="series-panel__table">
        <table>
          <caption class="sr-only">Vorschau aller Vorkommen</caption>
          <thead><tr><th scope="col">Serientermin</th><th scope="col">Ergebnis</th><th scope="col">Hinweis</th></tr></thead>
          <tbody>
            <tr v-if="!preview.occurrences.length"><td colspan="3">Keine Vorkommen im gewählten Zeitraum.</td></tr>
            <tr v-for="row in preview.occurrences" :key="row.date">
              <td>{{ formatDate(row.date) }}</td>
              <td><StatusBadge :label="actionLabels[row.action].label" :severity="actionLabels[row.action].severity" /></td>
              <td>
                {{ row.reason }}
                <router-link v-if="row.session_id" :to="`/training/sessions/${row.session_id}/plan`" @click="emit('navigate')">
                  Termin öffnen<template v-if="row.actual_date && row.actual_date !== row.date"> ({{ formatDate(row.actual_date) }})</template>
                </router-link>
                <ul v-if="row.warnings.length" class="series-panel__warnings">
                  <li v-for="warning in row.warnings" :key="warning"><StatusBadge label="Warnung" severity="warning" /> {{ warning }}</li>
                </ul>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import StatusBadge, { type StatusSeverity } from '@/components/common/StatusBadge.vue'
import { trainingSessionsApi } from '@/api/training'
import type { SeriesOccurrenceAction, SeriesPreview, SeriesWindow } from '@/types/training'

const props = defineProps<{ sessionId: number | null }>()
const emit = defineEmits<{ generated: [count: number]; navigate: [] }>()

const preview = ref<SeriesPreview | null>(null)
const windowStart = ref('')
const windowEnd = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const actionLabels: Record<SeriesOccurrenceAction, { label: string; severity: StatusSeverity }> = {
  new: { label: 'Neu', severity: 'success' },
  preserved: { label: 'Bleibt erhalten', severity: 'neutral' },
  skipped: { label: 'Ausgelassen', severity: 'info' },
  conflict: { label: 'Konflikt', severity: 'danger' },
}
const frequencyLabel = computed(() => ({ WEEKLY: 'wöchentlich', BIWEEKLY: 'zweiwöchentlich', MONTHLY: 'monatlich' })[preview.value?.frequency ?? 'WEEKLY'])

function formatDate(iso: string) {
  const [year, month, day] = iso.split('-')
  return `${day}.${month}.${year}`
}

function messages(value: unknown): string[] {
  if (typeof value === 'string') return [value]
  if (value && typeof value === 'object') return Object.values(value).flatMap(messages)
  return []
}

function windowParams(): SeriesWindow {
  return {
    ...(windowStart.value ? { window_start: windowStart.value } : {}),
    ...(windowEnd.value ? { window_end: windowEnd.value } : {}),
  }
}

function show(data: SeriesPreview) {
  preview.value = data
  windowStart.value = data.window_start
  windowEnd.value = data.window_end
}

async function load() {
  if (!props.sessionId) return
  loading.value = true
  error.value = ''
  try {
    show((await trainingSessionsApi.seriesPreview(props.sessionId, windowParams())).data)
  } catch (e: unknown) {
    const data = (e as { response?: { data?: unknown } }).response?.data
    error.value = messages(data).join(' ') || 'Vorschau konnte nicht geladen werden. Verbindung prüfen und erneut versuchen.'
  } finally {
    loading.value = false
  }
}

async function generate() {
  if (!props.sessionId || !preview.value || saving.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const { data } = await trainingSessionsApi.generateSeries(props.sessionId, {
      window_start: preview.value.window_start,
      window_end: preview.value.window_end,
      preview_token: preview.value.preview_token,
    })
    emit('generated', data.created)
    // Show the result together with the refreshed preview, never next to the stale one.
    preview.value = null
    await load()
    notice.value = `${data.created} Termine angelegt.`
  } catch (e: unknown) {
    const response = (e as { response?: { status?: number; data?: { preview?: SeriesPreview } } }).response
    if (response?.status === 409 && response.data?.preview) {
      show(response.data.preview)
      error.value = 'Die Serie wurde inzwischen geändert. Nichts wurde angelegt – bitte die aktualisierte Vorschau prüfen.'
    } else {
      error.value = messages(response?.data).join(' ') || 'Termine wurden nicht angelegt. Verbindung prüfen und erneut versuchen.'
    }
  } finally {
    saving.value = false
  }
}

watch(
  () => props.sessionId,
  () => {
    preview.value = null
    windowStart.value = ''
    windowEnd.value = ''
    notice.value = ''
    void load()
  },
  { immediate: true },
)
</script>

<style scoped src="./seriesPanel.css"></style>
