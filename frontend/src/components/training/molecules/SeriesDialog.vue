<template>
  <Dialog :visible="visible" header="Serientermine ergänzen" modal :style="{ width: '760px', maxWidth: 'calc(100vw - 24px)' }" @update:visible="close">
    <div class="series-dialog">
      <p class="series-dialog__intro">
        Fehlende Termine werden als eigenständige Entwürfe mit dem aktuell gespeicherten Ablauf angelegt.
        Vorhandene Termine, Pläne, Dienste und Anwesenheiten bleiben unverändert.
      </p>
      <form class="series-dialog__window" @submit.prevent="load">
        <label for="series-window-start">Von</label>
        <InputText id="series-window-start" v-model="windowStart" type="date" />
        <label for="series-window-end">Bis (höchstens 24 Monate)</label>
        <InputText id="series-window-end" v-model="windowEnd" type="date" />
        <Button type="submit" label="Vorschau aktualisieren" severity="secondary" :loading="loading" />
      </form>
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
      <Message v-if="notice" severity="success" :closable="false">{{ notice }}</Message>
      <div v-if="loading && !preview" class="series-dialog__loading" role="status">Vorschau lädt …</div>
      <template v-else-if="preview">
        <p class="series-dialog__summary" role="status">
          {{ preview.counts.new }} neu · {{ preview.counts.preserved }} vorhanden ·
          {{ preview.counts.skipped }} ausgelassen · {{ preview.counts.conflict }} Konflikte
          <span class="series-dialog__range">({{ formatDate(preview.window_start) }} – {{ formatDate(preview.window_end) }}, {{ frequencyLabel }})</span>
        </p>
        <div class="series-dialog__table">
          <table>
            <caption class="sr-only">Vorschau aller Vorkommen</caption>
            <thead><tr><th scope="col">Serientermin</th><th scope="col">Ergebnis</th><th scope="col">Hinweis</th></tr></thead>
            <tbody>
              <tr v-if="!preview.occurrences.length"><td colspan="3">Keine Vorkommen im gewählten Zeitraum.</td></tr>
              <tr v-for="row in preview.occurrences" :key="row.date" :class="`series-row--${row.action}`">
                <td>{{ formatDate(row.date) }}</td>
                <td><StatusBadge :label="actionLabels[row.action].label" :severity="actionLabels[row.action].severity" /></td>
                <td>
                  {{ row.reason }}
                  <template v-if="row.session_id">
                    <router-link :to="`/training/sessions/${row.session_id}/plan`" @click="close(false)">
                      Termin öffnen<template v-if="row.actual_date && row.actual_date !== row.date"> ({{ formatDate(row.actual_date) }})</template>
                    </router-link>
                  </template>
                  <ul v-if="row.warnings.length" class="series-warnings">
                    <li v-for="warning in row.warnings" :key="warning"><StatusBadge label="Warnung" severity="warning" /> {{ warning }}</li>
                  </ul>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>
    <template #footer>
      <Button label="Schließen" severity="secondary" @click="close(false)" />
      <Button
        :label="preview?.counts.new ? `${preview.counts.new} Termine anlegen` : 'Keine neuen Termine'"
        icon="pi pi-check"
        :disabled="!preview || !preview.counts.new || loading || saving"
        :loading="saving"
        @click="generate"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import StatusBadge, { type StatusSeverity } from '@/components/common/StatusBadge.vue'
import { trainingSessionsApi } from '@/api/training'
import type { SeriesOccurrenceAction, SeriesPreview, SeriesWindow } from '@/types/training'

const props = defineProps<{ visible: boolean; sessionId: number | null }>()
const emit = defineEmits<{ 'update:visible': [visible: boolean]; generated: [count: number] }>()

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
    notice.value = `${data.created} Termine angelegt.`
    emit('generated', data.created)
    await load()
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

function close(value = false) {
  emit('update:visible', value)
}

watch(
  () => props.visible,
  (visible) => {
    if (!visible) return
    preview.value = null
    windowStart.value = ''
    windowEnd.value = ''
    notice.value = ''
    void load()
  },
  { immediate: true },
)
</script>

<style scoped>
.series-dialog { display: grid; gap: var(--jf-space-3); }
.series-dialog p { margin: 0; }
.series-dialog__window { display: flex; flex-wrap: wrap; align-items: end; gap: var(--jf-space-2); }
.series-dialog__window label { font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.series-dialog__summary { font-weight: var(--jf-weight-semibold); }
.series-dialog__range { font-weight: normal; color: var(--jf-color-text-muted); }
.series-dialog__table { max-height: 50vh; overflow: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; vertical-align: top; border-bottom: 1px solid var(--jf-color-border); padding: var(--jf-space-1) var(--jf-space-2); }
.series-row--skipped td { color: var(--jf-color-text-muted); }
.series-warnings { display: grid; gap: var(--jf-space-0-5); margin: var(--jf-space-1) 0 0; padding-left: 0; list-style: none; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
