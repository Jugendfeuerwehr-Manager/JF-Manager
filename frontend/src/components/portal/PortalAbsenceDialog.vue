<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import Button from 'primevue/button'
import PortalSheet from './PortalSheet.vue'
import type { PortalAbsenceResult, PortalPerson, PortalReason } from '@/api/portal'
import { usePortalStore } from '@/stores/portal'
import { NOTE_MAX, REASONS, formatDay, formatTimeRange, personName } from '@/utils/portalSessions'

const props = defineProps<{ person: PortalPerson | null }>()
const emit = defineEmits<{ close: [], done: [result: PortalAbsenceResult] }>()

const portal = usePortalStore()
const from = ref('')
const to = ref('')
const reason = ref<PortalReason | ''>('')
const note = ref('')

const title = computed(() => {
  const name = personName(props.person)
  return name ? `${name} für einen Zeitraum abmelden` : 'Für einen Zeitraum abmelden'
})
const rangeValid = computed(() => !!from.value && !!to.value && from.value <= to.value)
const willCancel = computed(() => portal.absencePreview?.filter(r => r.action === 'cancel').length ?? 0)
const skipped = computed(() => portal.absencePreview?.filter(r => r.action === 'skip') ?? [])

// A changed range makes the preview stale.
watch([from, to], () => portal.resetAbsence())
onBeforeUnmount(() => portal.resetAbsence())

function range() {
  return { from: from.value, to: to.value, reason_category: reason.value, reason_note: note.value.trim() }
}
async function preview() { if (rangeValid.value) await portal.previewAbsence(range()) }
async function confirm() {
  const result = await portal.createAbsence(range())
  if (result) emit('done', result)
}
</script>

<template>
  <PortalSheet :title="title" title-id="absence-sheet-title" subtitle="Alle noch möglichen Dienste in diesem Zeitraum werden abgemeldet." @close="emit('close')">
    <div class="dates">
      <div class="field"><label for="absence-from">Von</label><input id="absence-from" v-model="from" type="date" /></div>
      <div class="field"><label for="absence-to">Bis</label><input id="absence-to" v-model="to" type="date" :min="from || undefined" /></div>
    </div>
    <fieldset class="reasons">
      <legend>Grund <span class="optional">(optional)</span></legend>
      <div class="chips">
        <label v-for="r in REASONS" :key="r.value" class="chip" :class="{ on: reason === r.value }">
          <input v-model="reason" type="radio" name="absence-reason" :value="r.value" />{{ r.label }}
        </label>
      </div>
    </fieldset>
    <div class="field">
      <label for="absence-note">Kurze Nachricht an die Dienstleitung <span class="optional">(optional)</span></label>
      <textarea id="absence-note" v-model="note" rows="2" :maxlength="NOTE_MAX" aria-describedby="absence-note-help"></textarea>
      <span id="absence-note-help" class="help">Bitte keine Gesundheitsdetails angeben. {{ note.length }}/{{ NOTE_MAX }} Zeichen</span>
    </div>

    <Button type="button" label="Vorschau anzeigen" severity="secondary" outlined :disabled="!rangeValid || portal.absenceBusy" :loading="portal.absenceBusy && !portal.absencePreview" @click="preview" />

    <section v-if="portal.absencePreview" class="preview" aria-live="polite" aria-label="Vorschau">
      <p v-if="!portal.absencePreview.length" class="none">In diesem Zeitraum gibt es keine Dienste.</p>
      <template v-else>
        <h3>Wird abgemeldet ({{ willCancel }})</h3>
        <p v-if="!willCancel" class="none">Kein Dienst muss abgemeldet werden.</p>
        <ul v-else>
          <li v-for="r in portal.absencePreview.filter(x => x.action === 'cancel')" :key="r.id">
            <span class="d">{{ formatDay(r.date) }} {{ formatTimeRange(r.start_time, r.end_time) }}</span> {{ r.title }}
          </li>
        </ul>
        <template v-if="skipped.length">
          <h3>Wird übersprungen ({{ skipped.length }})</h3>
          <ul>
            <li v-for="r in skipped" :key="r.id">
              <span class="d">{{ formatDay(r.date) }} {{ formatTimeRange(r.start_time, r.end_time) }}</span> {{ r.title }}
              <span class="why">({{ r.skip?.detail }})</span>
            </li>
          </ul>
        </template>
      </template>
    </section>

    <p v-if="portal.absenceError" class="error" role="alert">{{ portal.absenceError }}</p>
    <div class="buttons">
      <Button type="button" label="Abbrechen" severity="secondary" outlined :disabled="portal.absenceBusy" @click="emit('close')" />
      <Button type="button" label="Abmeldung senden" :loading="portal.absenceBusy && !!portal.absencePreview" :disabled="!portal.absencePreview || !willCancel || portal.absenceBusy" @click="confirm" />
    </div>
  </PortalSheet>
</template>

<style scoped>
.dates { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 14px; font-weight: 600; }
input[type='date'], textarea { font: inherit; font-size: 15px; min-height: 44px; box-sizing: border-box; padding: 10px 12px; border: 1px solid var(--p-form-field-border-color, var(--p-content-border-color)); border-radius: 10px; background: var(--p-form-field-background, var(--p-content-background)); color: var(--p-text-color); }
textarea { resize: none; }
.reasons { border: none; margin: 0; padding: 0; }
legend { font-size: 14px; font-weight: 600; margin-bottom: 8px; padding: 0; }
.optional { font-weight: 400; color: var(--p-text-muted-color); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { min-height: 44px; box-sizing: border-box; padding: 0 14px; border-radius: 22px; border: 1px solid var(--p-form-field-border-color, var(--p-content-border-color)); display: flex; align-items: center; gap: 6px; font-size: 14px; cursor: pointer; }
.chip input { margin: 0; accent-color: var(--p-primary-color); }
.chip.on { border: 2px solid var(--p-primary-color); background: var(--p-highlight-background); color: var(--p-highlight-color); font-weight: 600; }
.chip:focus-within { outline: 2px solid var(--p-primary-color); outline-offset: 2px; }
.help { font-size: 12px; color: var(--p-text-muted-color); }
.preview { padding: 10px 12px; border-radius: 10px; background: var(--p-content-hover-background, var(--p-surface-50)); font-size: 14px; }
.preview h3 { margin: 0 0 6px; font-size: 14px; font-weight: 650; }
.preview h3:not(:first-child) { margin-top: 12px; }
.preview ul { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 4px; }
.d { color: var(--p-text-muted-color); }
.why { color: var(--p-text-muted-color); font-size: 13px; }
.none { margin: 0; color: var(--p-text-muted-color); }
.error { margin: 0; font-size: 14px; color: var(--p-red-600); }
.app-dark .error { color: var(--p-red-300); }
.buttons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.buttons :deep(.p-button), .preview + .buttons :deep(.p-button) { min-height: 48px; border-radius: 12px; }
</style>
