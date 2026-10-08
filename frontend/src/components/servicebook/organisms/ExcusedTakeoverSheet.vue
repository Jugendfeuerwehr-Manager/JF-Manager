<template>
  <PortalSheet title="Als entschuldigt übernehmen" subtitle="Abmeldungen werden nur nach deiner Bestätigung übernommen." title-id="takeover-title" @close="$emit('close')">
    <p v-if="loading" role="status" class="info"><i class="pi pi-spin pi-spinner" aria-hidden="true"></i> Vorschau wird geladen …</p>
    <p v-else-if="error" role="alert" class="info info--error">
      <i class="pi pi-exclamation-triangle" aria-hidden="true"></i>{{ error }}
    </p>

    <template v-else-if="result">
      <p role="status" class="info info--ok"><i class="pi pi-check-circle" aria-hidden="true"></i>{{ result.applied }} {{ result.applied === 1 ? 'Person' : 'Personen' }} als entschuldigt übernommen.</p>
      <p v-if="result.applied < selectedCount" class="hint">Einige Personen wurden gleichzeitig geändert und blieben unverändert.</p>
      <button type="button" class="btn btn--primary" @click="$emit('close')">Fertig</button>
    </template>

    <template v-else-if="preview">
      <p class="hint">Nur Personen ohne erfasste Anwesenheit sind vorausgewählt.</p>
      <fieldset v-if="preview.apply.length" class="list">
        <legend>Abgemeldete Personen</legend>
        <label v-for="person in preview.apply" :key="person.member_id" class="item">
          <input v-model="selected" type="checkbox" :value="person.member_id" />
          <span class="item__name">{{ person.name }}</span>
          <span class="item__hint">noch nicht erfasst</span>
        </label>
      </fieldset>
      <p v-else class="hint">Keine abgemeldeten Personen ohne erfasste Anwesenheit.</p>
      <ul v-if="preview.skipped.length" class="skipped" aria-label="Nicht betroffen">
        <li v-for="person in preview.skipped" :key="person.member_id">
          <i class="pi pi-info-circle" aria-hidden="true"></i>
          <strong>{{ person.name }}</strong> {{ skipText(person.reason) }}
        </li>
      </ul>
      <p class="hint">Bereits erfasste Werte werden nie überschrieben. Ändert jemand gleichzeitig dieselbe Person, wirst du gefragt.</p>
      <p v-if="confirmError" role="alert" class="info info--error"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i>{{ confirmError }}</p>
      <div class="actions">
        <button type="button" class="btn" @click="$emit('close')">Abbrechen</button>
        <button type="button" class="btn btn--primary" :disabled="!selected.length || saving" @click="confirm">
          {{ saving ? 'Übernehme …' : `${selected.length} übernehmen` }}
        </button>
      </div>
    </template>
  </PortalSheet>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PortalSheet from '@/components/portal/PortalSheet.vue'
import { useServiceRegistrationsStore } from '@/stores/serviceRegistrations'
import type { ApplyExcusedPreview } from '@/types/servicebook'
import { getApiErrorMessage } from '@/utils/apiError'

const props = defineProps<{ serviceId: number }>()
const emit = defineEmits<{ close: []; applied: [count: number] }>()
const store = useServiceRegistrationsStore()

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const confirmError = ref('')
const preview = ref<ApplyExcusedPreview | null>(null)
const result = ref<ApplyExcusedPreview | null>(null)
const selected = ref<number[]>([])
const selectedCount = computed(() => selected.value.length)

function skipText(reason: 'has_attendance' | 'not_cancelled') {
  return reason === 'has_attendance' ? 'ist bereits erfasst und bleibt unverändert.' : 'ist nicht abgemeldet.'
}

onMounted(async () => {
  try {
    preview.value = await store.previewExcused(props.serviceId)
    selected.value = preview.value.apply.map((p) => p.member_id)
  } catch (e) {
    error.value = getApiErrorMessage(e, 'Die Vorschau konnte nicht geladen werden.')
  } finally {
    loading.value = false
  }
})

async function confirm() {
  saving.value = true
  confirmError.value = ''
  try {
    result.value = await store.applyExcused(props.serviceId, [...selected.value])
    emit('applied', result.value.applied)
  } catch (e) {
    confirmError.value = getApiErrorMessage(e, 'Die Übernahme ist fehlgeschlagen. Bitte erneut versuchen.')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.hint { margin: 0; font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.info { display: flex; align-items: center; gap: var(--jf-space-1); margin: 0; }
.info--ok { color: var(--p-green-800); font-weight: var(--jf-weight-semibold); }
.info--error { color: var(--p-red-800); font-weight: var(--jf-weight-semibold); }
.app-dark .info--ok { color: var(--p-green-300); }
.app-dark .info--error { color: var(--p-red-300); }
.list { margin: 0; padding: 0; border: 0; display: flex; flex-direction: column; gap: var(--jf-space-1); }
.list legend { padding: 0; margin-bottom: var(--jf-space-1); font-weight: var(--jf-weight-bold); }
.item { display: flex; align-items: center; gap: var(--jf-space-1-5); min-height: 3rem; padding: 0 var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); }
.item input { width: 1.5rem; height: 1.5rem; flex: none; }
.item__name { flex: 1; min-width: 0; font-weight: var(--jf-weight-semibold); overflow-wrap: anywhere; }
.item__hint { font-size: var(--jf-text-xs); color: var(--jf-color-text-muted); }
.skipped { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: var(--jf-space-0-5); font-size: var(--jf-text-sm); }
.actions { display: flex; gap: var(--jf-space-1); }
.btn { flex: 1; min-height: 3rem; padding: 0 var(--jf-space-2); border: 1px solid var(--p-surface-300); border-radius: var(--jf-radius-md); background: transparent; color: var(--jf-color-text); font: inherit; font-weight: var(--jf-weight-semibold); cursor: pointer; }
.btn--primary { border-color: var(--jf-color-primary); background: var(--jf-color-primary); color: var(--jf-color-on-primary); }
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
