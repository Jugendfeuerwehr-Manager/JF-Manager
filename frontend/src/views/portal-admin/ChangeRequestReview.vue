<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import Button from 'primevue/button'
import ContactLink from '@/components/common/ContactLink.vue'
import type { ChangeDecision, Review } from '@/types/changeRequests'
import { requestDateTime } from '@/utils/changeRequestFields'

const props = defineProps<{ review: Review, busy?: boolean, error?: string | null, errorFields?: string[] }>()
const emit = defineEmits<{ decide: [payload: { decisions: Record<string, ChangeDecision>, confirm_conflicts: string[], note: string }] }>()

const readonly = computed(() => props.review.status !== 'open')
const locked = computed(() => readonly.value || props.review.own)

const decisions = reactive<Record<string, ChangeDecision | undefined>>({})
const confirmed = reactive<Record<string, boolean>>({})
const note = ref('')

// A new request or a new version starts with a clean slate: the data under review changed.
watch(() => [props.review.id, props.review.version], () => {
  for (const key of Object.keys(decisions)) delete decisions[key]
  for (const key of Object.keys(confirmed)) delete confirmed[key]
  note.value = ''
}, { immediate: true })

const canApply = (field: { field: string, conflict: boolean }) => !field.conflict || !!confirmed[field.field]
const undecided = computed(() => props.review.fields.filter(f => !decisions[f.field]).length)
const canSubmit = computed(() => !locked.value && !props.busy && undecided.value === 0)

function decide(field: string, value: ChangeDecision) { decisions[field] = value }
function confirm(field: string, on: boolean) {
  confirmed[field] = on
  if (!on && decisions[field] === 'apply') decisions[field] = undefined
}
function setAll(value: ChangeDecision) {
  for (const f of props.review.fields) {
    if (value === 'reject' || canApply(f)) decisions[f.field] = value
  }
}
function submit() {
  if (!canSubmit.value) return
  const out: Record<string, ChangeDecision> = {}
  for (const f of props.review.fields) out[f.field] = decisions[f.field]!
  const confirm_conflicts = props.review.fields.filter(f => f.conflict && out[f.field] === 'apply' && confirmed[f.field]).map(f => f.field)
  emit('decide', { decisions: out, confirm_conflicts, note: note.value.trim() })
}

const decisionText = (d?: ChangeDecision) => (d === 'apply' ? 'Übernommen' : d === 'reject' ? 'Abgelehnt' : '–')
const submitLabel = computed(() => (undecided.value ? `Entscheidung speichern (${undecided.value} offen)` : 'Entscheidung speichern'))

const contactFieldKind = (field: string): 'phone' | 'email' | null => {
  if (field === 'phone' || field === 'mobile') return 'phone'
  if (field === 'email' || field === 'email2') return 'email'
  return null
}
</script>

<template>
  <div class="review">
    <div class="intro">
      <h2>{{ review.person_name }} · {{ review.kind === 'parent' ? 'Elternteil' : 'Mitglied' }}</h2>
      <span class="meta">Beantragt von {{ review.requested_by }} am {{ requestDateTime(review.created_at) }}<template v-if="review.updated_at !== review.created_at"> · zuletzt geändert {{ requestDateTime(review.updated_at) }}</template></span>
      <span v-if="readonly" class="status"><i class="pi pi-check-circle" aria-hidden="true"></i> {{ review.status_label }}<template v-if="review.decided_at"> am {{ requestDateTime(review.decided_at) }}</template></span>
    </div>

    <p v-if="review.own && !readonly" class="own" role="status"><i class="pi pi-lock" aria-hidden="true"></i> Eigene Anträge gibt eine andere Person frei.</p>

    <ul class="fields">
      <li class="row head" aria-hidden="true">
        <span>Feld</span><span>Bei Antrag</span><span>Aktuell</span><span>Beantragt</span><span>Entscheidung</span>
      </li>
      <li v-for="f in review.fields" :key="f.field" class="row" :class="{ conflict: f.conflict && !readonly, flagged: errorFields?.includes(f.field) }" :data-field="f.field">
        <span class="label">{{ f.label }}</span>
        <span class="cell" data-label="Bei Antrag">
          <ContactLink v-if="contactFieldKind(f.field) && f.old" :kind="contactFieldKind(f.field)!" :value="f.old" />
          <span v-else>{{ f.old || '–' }}</span>
        </span>
        <span class="cell" data-label="Aktuell">
          <ContactLink v-if="contactFieldKind(f.field) && f.current" :kind="contactFieldKind(f.field)!" :value="f.current" />
          <span v-else>{{ f.current || '–' }}</span>
          <span v-if="f.conflict && !readonly" class="warn"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> Seit Antrag geändert</span>
        </span>
        <span class="cell new" data-label="Beantragt">
          <ContactLink v-if="contactFieldKind(f.field) && f.new" :kind="contactFieldKind(f.field)!" :value="f.new" />
          <span v-else>{{ f.new || '–' }}</span>
        </span>
        <span class="cell decide" data-label="Entscheidung">
          <span v-if="readonly" class="done"><i :class="f.decision === 'apply' ? 'pi pi-check' : 'pi pi-times'" aria-hidden="true"></i> {{ decisionText(f.decision) }}</span>
          <template v-else>
            <label v-if="f.conflict" class="confirm">
              <input type="checkbox" :checked="!!confirmed[f.field]" :disabled="locked" @change="confirm(f.field, ($event.target as HTMLInputElement).checked)" />
              Aktuellen Wert überschreiben
            </label>
            <div class="toggle" role="radiogroup" :aria-label="`Entscheidung für ${f.label}`">
              <button type="button" role="radio" :aria-checked="decisions[f.field] === 'apply'" :class="{ on: decisions[f.field] === 'apply', accept: true }" :disabled="locked || !canApply(f)" @click="decide(f.field, 'apply')">
                <i v-if="decisions[f.field] === 'apply'" class="pi pi-check" aria-hidden="true"></i>Übernehmen
              </button>
              <button type="button" role="radio" :aria-checked="decisions[f.field] === 'reject'" :class="{ on: decisions[f.field] === 'reject' }" :disabled="locked" @click="decide(f.field, 'reject')">
                <i v-if="decisions[f.field] === 'reject'" class="pi pi-times" aria-hidden="true"></i>Ablehnen
              </button>
            </div>
            <span v-if="f.conflict && !confirmed[f.field]" class="hint">Bitte ausdrücklich entscheiden: Zum Übernehmen erst die Überschreibung bestätigen.</span>
          </template>
        </span>
      </li>
    </ul>

    <div v-if="!readonly" class="note">
      <label for="review-note">Nachricht an {{ review.requested_by }} <span class="optional">(optional, wird mit der Entscheidung gesendet)</span></label>
      <textarea id="review-note" v-model="note" rows="2" :disabled="locked"></textarea>
    </div>
    <p v-else-if="review.decision_note" class="note-read">Nachricht: {{ review.decision_note }}</p>

    <p v-if="error" class="error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i> {{ error }}</p>

    <div v-if="!readonly" class="footer">
      <span class="muted">Die Übernahme wird protokolliert. „Alle übernehmen“ lässt Felder mit Konflikt aus, solange die Überschreibung nicht bestätigt ist.</span>
      <div class="buttons">
        <Button type="button" label="Alle ablehnen" severity="secondary" outlined :disabled="locked || busy" @click="setAll('reject')" />
        <Button type="button" label="Alle übernehmen" severity="secondary" outlined :disabled="locked || busy" @click="setAll('apply')" />
        <Button type="button" :label="submitLabel" :loading="busy" :disabled="!canSubmit" @click="submit" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.review { display: flex; flex-direction: column; gap: 16px; }
.intro { display: flex; flex-direction: column; gap: 4px; }
h2 { margin: 0; font-size: 19px; font-weight: 700; }
.meta { font-size: 14px; color: var(--p-text-muted-color); }
.status { font-size: 14px; font-weight: 600; display: inline-flex; gap: 6px; align-items: center; }
.own { margin: 0; display: flex; gap: 8px; align-items: center; padding: 10px 12px; border-radius: 10px; background: var(--p-orange-50); color: var(--p-orange-900); border: 1px solid var(--p-orange-200); font-size: 14px; }
.fields { list-style: none; margin: 0; padding: 0; border: 1px solid var(--p-content-border-color); border-radius: 12px; overflow: hidden; }
.row { display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; border-top: 1px solid var(--p-content-border-color); font-size: 14px; min-width: 0; overflow-wrap: anywhere; }
.row:first-child { border-top: none; }
.row.head { display: none; }
.row.conflict { background: var(--p-orange-50); }
.row.flagged { outline: 2px solid var(--p-red-600); outline-offset: -2px; }
.label { font-weight: 600; }
.cell::before { content: attr(data-label) ': '; font-size: 12px; color: var(--p-text-muted-color); }
.new { font-weight: 650; }
.warn { display: flex; gap: 4px; align-items: center; margin-top: 2px; font-size: 12px; font-weight: 650; color: var(--p-orange-800); }
.decide::before { display: none; }
.decide { display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }
.confirm { display: flex; gap: 8px; align-items: center; min-height: 44px; font-size: 13px; cursor: pointer; }
.confirm input { width: 20px; height: 20px; accent-color: var(--p-primary-color); }
.toggle { display: inline-flex; border: 1px solid var(--p-content-border-color); border-radius: 10px; overflow: hidden; }
.toggle button { white-space: nowrap; min-height: 44px; padding: 0 14px; border: none; background: var(--p-content-background); color: var(--p-text-color); font: inherit; font-size: 13px; cursor: pointer; display: inline-flex; gap: 6px; align-items: center; }
.toggle button + button { border-left: 1px solid var(--p-content-border-color); }
.toggle button.on { background: var(--p-surface-700); color: var(--p-surface-0); font-weight: 650; }
.toggle button.on.accept { background: var(--p-green-700); }
.toggle button:disabled { opacity: 0.5; cursor: not-allowed; }
.hint { font-size: 12px; color: var(--p-orange-800); }
.done { display: inline-flex; gap: 6px; align-items: center; font-weight: 600; }
.note, .note-read { display: flex; flex-direction: column; gap: 6px; margin: 0; font-size: 14px; }
.note label { font-weight: 600; }
.optional { font-weight: 400; color: var(--p-text-muted-color); }
textarea { font: inherit; font-size: 14px; padding: 10px 12px; border: 1px solid var(--p-form-field-border-color, var(--p-content-border-color)); border-radius: 10px; resize: vertical; background: var(--p-form-field-background, var(--p-content-background)); color: var(--p-text-color); }
.error { margin: 0; font-size: 14px; color: var(--p-red-700); }
.footer { display: flex; flex-direction: column; gap: 12px; border-top: 1px solid var(--p-content-border-color); padding-top: 16px; }
.muted { font-size: 13px; color: var(--p-text-muted-color); }
.buttons { display: flex; flex-wrap: wrap; gap: 8px; }
.buttons :deep(.p-button) { min-height: 44px; border-radius: 10px; }
.app-dark .own, .app-dark .row.conflict { background: color-mix(in srgb, var(--p-orange-400), transparent 90%); color: inherit; border-color: color-mix(in srgb, var(--p-orange-400), transparent 60%); }
.app-dark .warn, .app-dark .hint { color: var(--p-orange-300); }
.app-dark .error { color: var(--p-red-300); }
.app-dark .toggle button.on.accept { background: var(--p-green-600); }
@media (min-width: 900px) {
  .row { display: grid; grid-template-columns: 0.8fr 1fr 1.2fr 1.2fr minmax(max-content, 1.6fr); gap: 12px; align-items: start; }
  .row.head { display: grid; background: var(--p-content-hover-background, var(--p-surface-50)); font-size: 12px; font-weight: 650; text-transform: uppercase; letter-spacing: 0.04em; color: var(--p-text-muted-color); }
  .cell::before { display: none; }
}
</style>
