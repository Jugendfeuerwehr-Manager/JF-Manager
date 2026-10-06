<template>
  <div class="series-panel">
    <p>
      Der gespeicherte Stand dieses Termins (Titel, Zeiten, Ort, Gruppen und Ablauf mit eigenen Medienkopien) wird auf
      spätere Termine der Serie übertragen. Vergangene, abgeschlossene, abgesagte und dokumentierte Termine bleiben
      immer unverändert; abweichende Einzeltermine nur, wenn sie ausdrücklich ausgewählt werden.
    </p>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Message v-if="notice" severity="success" :closable="false">{{ notice }}</Message>
    <div v-if="loading && !preview" role="status">Vorschau lädt …</div>
    <template v-else-if="preview">
      <p class="series-panel__summary" role="status">
        {{ preview.counts.update }} werden geändert · {{ preview.counts.deviating }} abweichend erhalten ·
        {{ preview.counts.history }} historisch · {{ preview.counts.unchanged }} unverändert · {{ preview.counts.conflict }} Konflikte
      </p>
      <div class="series-panel__table">
        <table>
          <caption class="sr-only">Vorschau der folgenden Termine</caption>
          <thead><tr><th scope="col">Termin</th><th scope="col">Ergebnis</th><th scope="col">Änderungen</th></tr></thead>
          <tbody>
            <tr v-if="!preview.occurrences.length"><td colspan="3">Keine folgenden Termine in dieser Serie.</td></tr>
            <tr v-for="row in preview.occurrences" :key="row.session_id ?? row.original_date">
              <td>
                {{ formatDate(row.date) }}<template v-if="row.date !== row.original_date"> (Serie: {{ formatDate(row.original_date) }})</template>
                <br />
                <router-link v-if="row.session_id" :to="`/training/sessions/${row.session_id}/plan`" @click="emit('navigate')">{{ row.title }}</router-link>
                <span v-else>{{ row.title }}</span>
              </td>
              <td>
                <StatusBadge :label="actionLabels[row.action].label" :severity="actionLabels[row.action].severity" />
                <label v-if="row.overridable && row.session_id" class="series-panel__override">
                  <Checkbox :model-value="included.includes(row.session_id)" :binary="true" :input-id="`override-${row.session_id}`" @update:model-value="toggle(row.session_id, $event)" />
                  <span>Trotzdem überschreiben</span>
                </label>
              </td>
              <td>
                {{ row.reason }}
                <ul v-if="row.changes.length" class="series-panel__changes">
                  <li v-for="change in row.changes" :key="change">{{ change }}</li>
                </ul>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
    <div class="series-panel__actions">
      <Button
        :label="preview?.counts.update ? `${preview.counts.update} Folgetermine ändern` : 'Keine Folgetermine zu ändern'"
        icon="pi pi-check"
        :disabled="!preview || !preview.counts.update || loading || saving"
        :loading="saving"
        @click="apply"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import StatusBadge, { type StatusSeverity } from '@/components/common/StatusBadge.vue'
import { trainingSessionsApi } from '@/api/training'
import type { PropagationAction, PropagationPreview } from '@/types/training'

const props = defineProps<{ sessionId: number | null }>()
const emit = defineEmits<{ propagated: [count: number]; navigate: [] }>()

const preview = ref<PropagationPreview | null>(null)
const included = ref<number[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const actionLabels: Record<PropagationAction, { label: string; severity: StatusSeverity }> = {
  update: { label: 'Wird geändert', severity: 'info' },
  unchanged: { label: 'Bereits gleich', severity: 'neutral' },
  deviating: { label: 'Abweichend – bleibt', severity: 'warning' },
  history: { label: 'Historisch – bleibt', severity: 'neutral' },
  conflict: { label: 'Konflikt', severity: 'danger' },
}

function formatDate(iso: string) {
  const [year, month, day] = iso.split('-')
  return `${day}.${month}.${year}`
}

function messages(value: unknown): string[] {
  if (typeof value === 'string') return [value]
  if (value && typeof value === 'object') return Object.values(value).flatMap(messages)
  return []
}

async function load() {
  if (!props.sessionId) return
  loading.value = true
  error.value = ''
  try {
    preview.value = (await trainingSessionsApi.propagationPreview(props.sessionId, { include_deviating: included.value })).data
  } catch (e: unknown) {
    const data = (e as { response?: { data?: unknown } }).response?.data
    error.value = messages(data).join(' ') || 'Vorschau konnte nicht geladen werden. Verbindung prüfen und erneut versuchen.'
  } finally {
    loading.value = false
  }
}

function toggle(id: number, value: boolean) {
  included.value = value ? [...included.value, id] : included.value.filter((item) => item !== id)
  // The selection is part of the confirmed preview; reload before applying.
  void load()
}

async function apply() {
  if (!props.sessionId || !preview.value || saving.value) return
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const { data } = await trainingSessionsApi.propagateSeries(props.sessionId, {
      include_deviating: included.value,
      preview_token: preview.value.preview_token,
    })
    notice.value = `${data.updated} Folgetermine geändert.`
    emit('propagated', data.updated)
    included.value = []
    await load()
  } catch (e: unknown) {
    const response = (e as { response?: { status?: number; data?: { preview?: PropagationPreview } } }).response
    if (response?.status === 409 && response.data?.preview) {
      preview.value = response.data.preview
      error.value = 'Serie oder Termine wurden inzwischen geändert. Nichts wurde übertragen – bitte die aktualisierte Vorschau prüfen.'
    } else {
      error.value = messages(response?.data).join(' ') || 'Nicht übertragen. Verbindung prüfen und erneut versuchen.'
    }
  } finally {
    saving.value = false
  }
}

watch(
  () => props.sessionId,
  () => {
    preview.value = null
    included.value = []
    notice.value = ''
    void load()
  },
  { immediate: true },
)
</script>

<style scoped src="./seriesPanel.css"></style>
<style scoped>
.series-panel__override { display: flex; align-items: center; gap: var(--jf-space-1); margin-top: var(--jf-space-1); font-size: var(--jf-text-sm); }
</style>
