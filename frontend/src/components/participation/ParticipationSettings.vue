<template>
  <div class="part-settings">
    <p v-if="store.loading && !store.draft" role="status"><i class="pi pi-spin pi-spinner" aria-hidden="true"></i> Teilnahme-Einstellungen werden geladen …</p>
    <div v-else-if="!store.draft" role="alert">
      <p>{{ store.error ?? 'Die Teilnahme-Einstellungen sind nicht verfügbar.' }}</p>
      <Button label="Erneut laden" severity="secondary" @click="store.loadConfig(sessionId)" />
    </div>
    <template v-else>
      <div v-if="store.conflict" class="part-settings__conflict" role="alert">
        <p><i class="pi pi-exclamation-triangle" aria-hidden="true"></i>{{ STALE_MESSAGE }} Dein Entwurf bleibt erhalten.</p>
        <div class="part-settings__row">
          <Button label="Meinen Entwurf auf neuer Fassung speichern" severity="secondary" @click="store.keepDraftOnServerVersion()" />
          <Button label="Neue Fassung laden und Entwurf verwerfen" severity="secondary" text @click="store.useServerVersion()" />
        </div>
      </div>
      <p v-else-if="store.error" class="part-settings__error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ store.error }}</p>

      <div class="part-settings__layout">
        <div class="part-settings__main">
          <fieldset class="part-card" :disabled="readonly">
            <legend class="part-card__title">Teilnahmemodus</legend>
            <div class="part-modes">
              <label v-for="mode in MODES" :key="mode.value" class="part-mode" :class="{ 'part-mode--active': store.draft.mode === mode.value }">
                <input type="radio" name="participation-mode" :value="mode.value" :checked="store.draft.mode === mode.value" @change="store.setMode(mode.value)">
                <span>
                  <strong>{{ mode.label }}</strong>
                  <span class="part-hint">{{ mode.text }}</span>
                </span>
              </label>
            </div>
            <p v-if="store.draft.mode === 'assignment'" class="part-hint">
              <i class="pi pi-info-circle" aria-hidden="true"></i>Positionen und die Zuteilung durch Verantwortliche folgen in einem weiteren Schritt.
            </p>
          </fieldset>

          <fieldset class="part-card" :disabled="readonly">
            <legend class="part-card__title">Fristen</legend>
            <p class="part-hint">Standard: Anmeldung {{ store.config?.defaults.registration_offset_h }} h, Abmeldung {{ store.config?.defaults.cancellation_offset_h }} h vor Beginn.</p>
            <div class="part-grid">
              <div v-for="field in DEADLINES" :key="field.key" class="part-field">
                <label :for="`part-${field.key}`">{{ field.label }}</label>
                <input
                  :id="`part-${field.key}`"
                  type="datetime-local"
                  class="part-input"
                  :value="deadlineValue(field.key)"
                  :aria-describedby="`part-${field.key}-hint`"
                  @change="setDeadline(field.key, ($event.target as HTMLInputElement).value)"
                >
                <span :id="`part-${field.key}-hint`" class="part-hint">
                  {{ store.draft[field.key] ? 'Eigene Frist' : field.fallback }}
                  <Button v-if="store.draft[field.key]" label="Auf Standard zurücksetzen" size="small" text @click="store.draft[field.key] = null" />
                </span>
                <span v-if="store.fieldErrors[field.key]" class="part-error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ store.fieldErrors[field.key] }}</span>
              </div>
            </div>
          </fieldset>

          <fieldset class="part-card" :disabled="readonly">
            <legend class="part-card__title">Plätze und Warteliste</legend>
            <p v-if="optOut" id="part-capacity-note" class="part-hint">
              <i class="pi pi-lock" aria-hidden="true"></i>Im Modus „Abmeldung“ sind alle der Zielgruppe eingeplant. Höchstzahl, Mindestzahl und Warteliste gibt es nur bei Anmeldung oder Zuteilung.
            </p>
            <div class="part-grid">
              <div class="part-field">
                <label for="part-max">Höchstzahl</label>
                <input id="part-max" type="number" min="1" class="part-input" :disabled="optOut" :aria-describedby="optOut ? 'part-capacity-note' : undefined" :value="store.draft.max_participants ?? ''" placeholder="unbegrenzt" @input="setNumber('max_participants', $event)">
                <span v-if="store.fieldErrors.max_participants" class="part-error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ store.fieldErrors.max_participants }}</span>
              </div>
              <div class="part-field">
                <label for="part-min">Mindestzahl</label>
                <input id="part-min" type="number" min="0" class="part-input" :disabled="optOut" :aria-describedby="optOut ? 'part-capacity-note' : undefined" :value="store.draft.min_participants ?? ''" placeholder="keine" @input="setNumber('min_participants', $event)">
                <span v-if="store.fieldErrors.min_participants" class="part-error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ store.fieldErrors.min_participants }}</span>
              </div>
              <div class="part-field">
                <label for="part-waitlist">Nachrücken von der Warteliste</label>
                <select id="part-waitlist" v-model="store.draft.waitlist_mode" class="part-input" :disabled="optOut" :aria-describedby="optOut ? 'part-capacity-note' : undefined">
                  <option value="auto">Automatisch nachrücken</option>
                  <option value="manual">Manuell durch Verantwortliche</option>
                </select>
              </div>
            </div>
          </fieldset>

          <section class="part-card" aria-labelledby="part-who-title">
            <h3 id="part-who-title" class="part-card__title">Wer darf teilnehmen?</h3>
            <fieldset class="part-bare" :disabled="readonly">
              <RuleBuilder
                v-model="store.draft.eligibility"
                uid="part-rule"
                :errors="store.ruleErrors"
                :options="ruleOptions.options.value"
                :loading="ruleOptions.loading.value"
                :summary="summary"
              />
            </fieldset>
            <p v-if="ruleOptions.error.value" class="part-error" role="alert">{{ ruleOptions.error.value }}</p>
          </section>

          <fieldset class="part-card" :disabled="readonly">
            <legend class="part-card__title">Hinweis für Teilnehmende</legend>
            <label for="part-note" class="part-hint">Kurzer Klartext, z. B. Treffpunkt oder Kleidung. Erscheint im Portal.</label>
            <textarea id="part-note" v-model="store.draft.public_note" class="part-input part-textarea" rows="3" maxlength="1000"></textarea>
            <span v-if="store.fieldErrors.public_note" class="part-error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ store.fieldErrors.public_note }}</span>
            <label class="part-check"><input v-model="store.draft.portal_visible" type="checkbox">Im Portal für Eltern und Mitglieder sichtbar</label>
          </fieldset>

          <p class="part-hint"><i class="pi pi-info-circle" aria-hidden="true"></i>Positionen, Mindestbesetzung und Vorlagen folgen.</p>
        </div>

        <aside class="part-settings__aside">
          <RulePreview :preview="store.preview" :loading="store.previewLoading" :error="store.previewError" :errors="store.ruleErrors" />
        </aside>
      </div>

      <div v-if="!readonly" class="part-savebar" role="group" aria-label="Speichern">
        <span class="part-hint" role="status">
          <template v-if="store.saving">Speichert …</template>
          <template v-else-if="store.dirty"><i class="pi pi-pencil" aria-hidden="true"></i>Ungespeicherte Änderungen</template>
          <template v-else-if="store.notice"><i class="pi pi-check" aria-hidden="true"></i>{{ store.notice }}</template>
          <template v-else>Keine Änderungen</template>
        </span>
        <Button label="Verwerfen" severity="secondary" :disabled="!store.dirty || store.saving" @click="store.discard()" />
        <Button label="Speichern" icon="pi pi-save" :disabled="!store.dirty" :loading="store.saving" @click="store.saveConfig()" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import RuleBuilder from './RuleBuilder.vue'
import RulePreview from './RulePreview.vue'
import { STALE_MESSAGE, useParticipationStore } from '@/stores/participation'
import { useRuleOptions } from '@/composables/useRuleOptions'
import type { ParticipationMode } from '@/api/participation'

const props = defineProps<{ sessionId: number, readonly?: boolean }>()
const store = useParticipationStore()
const ruleOptions = useRuleOptions()

const MODES: Array<{ value: ParticipationMode, label: string, text: string }> = [
  { value: 'opt_out', label: 'Abmeldung', text: 'Alle der Zielgruppe sind eingeplant und melden sich ab, wenn sie nicht kommen.' },
  { value: 'opt_in', label: 'Anmeldung', text: 'Wer passt, meldet sich an. Optional mit Höchstzahl und Warteliste.' },
  { value: 'assignment', label: 'Zuteilung', text: 'Passende Personen bewerben sich, Verantwortliche teilen zu.' },
]
type DeadlineKey = 'registration_opens_at' | 'registration_closes_at' | 'cancellation_closes_at'
const DEADLINES: Array<{ key: DeadlineKey, label: string, fallback: string }> = [
  { key: 'registration_opens_at', label: 'Meldungen möglich ab', fallback: 'Standard: mit Veröffentlichung' },
  { key: 'registration_closes_at', label: 'Anmeldeschluss (gilt für Anmelden und Bewerben)', fallback: 'Standard der Abteilung' },
  { key: 'cancellation_closes_at', label: 'Abmeldeschluss', fallback: 'Standard der Abteilung' },
]

const optOut = computed(() => store.draft?.mode === 'opt_out')
const summary = computed(() => store.preview?.summary ?? store.config?.eligibility_summary ?? null)

/** `datetime-local` works with local wall-clock time without zone. */
function toLocalInput(iso: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}
function deadlineValue(key: DeadlineKey): string {
  const own = store.draft?.[key]
  if (own) return toLocalInput(own)
  return toLocalInput(store.config?.effective[key] ?? null)
}
function setDeadline(key: DeadlineKey, value: string) {
  if (!store.draft) return
  store.draft[key] = value ? new Date(value).toISOString() : null
}
function setNumber(key: 'max_participants' | 'min_participants', event: Event) {
  if (!store.draft) return
  const raw = (event.target as HTMLInputElement).value
  store.draft[key] = raw === '' ? null : Number(raw)
}

async function load(id: number) {
  await store.loadConfig(id)
  if (store.draft) void store.runPreview(store.draft.eligibility)
}
onMounted(() => {
  void ruleOptions.load()
  void load(props.sessionId)
})
watch(() => props.sessionId, id => { void load(id) })
watch(() => store.draft?.eligibility, (rule, before) => {
  // Only edits trigger a request; replacing the whole draft (load, discard) is handled by the callers.
  if (rule && before && JSON.stringify(rule) !== JSON.stringify(before)) store.schedulePreview(rule)
}, { deep: true })
onBeforeUnmount(() => store.cancelPreview())
</script>

<style scoped>
.part-settings { display: grid; gap: var(--jf-space-2); }
.part-settings__layout { display: flex; flex-wrap: wrap; gap: var(--jf-space-3); align-items: flex-start; }
.part-settings__main { flex: 999 1 26rem; min-width: 0; display: grid; gap: var(--jf-space-2); }
.part-settings__aside { flex: 1 1 18rem; min-width: 0; position: sticky; top: 0; }
.part-card { display: grid; gap: var(--jf-space-1-5); margin: 0; padding: var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-card); min-width: 0; }
.part-card__title { margin: 0; padding: 0 var(--jf-space-0-5); font-size: var(--jf-text-lg); font-weight: var(--jf-weight-bold); }
.part-bare { border: 0; margin: 0; padding: 0; min-width: 0; }
.part-modes { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: var(--jf-space-1-5); }
.part-mode { display: flex; gap: var(--jf-space-1); align-items: flex-start; min-height: var(--jf-touch-target); padding: var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); cursor: pointer; }
.part-mode--active { border-color: var(--jf-color-primary); background: var(--jf-color-selected); color: var(--jf-color-selected-text); box-shadow: inset 0 0 0 1px var(--jf-color-primary); }
.part-mode input { margin-top: 4px; width: 1.1rem; height: 1.1rem; }
.part-mode span { display: grid; gap: 2px; }
.part-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: var(--jf-space-2); }
.part-field { display: grid; gap: var(--jf-space-0-5); align-content: start; }
.part-field > label { font-weight: var(--jf-weight-semibold); }
.part-input { min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-sm); background: var(--jf-color-card); color: var(--jf-color-text); font: inherit; box-sizing: border-box; width: 100%; }
.part-input:disabled { opacity: 0.6; cursor: not-allowed; }
.part-textarea { padding: var(--jf-space-1) var(--jf-space-1-5); resize: vertical; }
.part-check { display: flex; align-items: center; gap: var(--jf-space-1); min-height: var(--jf-touch-target); }
.part-check input { width: 1.1rem; height: 1.1rem; }
.part-hint { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); margin: 0; }
.part-hint i, .part-error i { margin-right: var(--jf-space-0-5); }
.part-error, .part-settings__error { color: var(--p-red-600); font-size: var(--jf-text-sm); margin: 0; }
.part-settings__conflict { padding: var(--jf-space-1-5) var(--jf-space-2); border: 1px solid var(--p-amber-600); border-radius: var(--jf-radius-md); background: var(--jf-color-card); }
.part-settings__conflict p { margin: 0 0 var(--jf-space-1); }
.part-settings__row { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); }
.part-savebar { position: sticky; bottom: 0; display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: var(--jf-space-1); padding: var(--jf-space-1-5) var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); background: var(--jf-color-card); }
.part-savebar .part-hint { margin-right: auto; }
.app-dark .part-error, .app-dark .part-settings__error { color: var(--p-red-300); }
@media (max-width: 900px) { .part-settings__aside { position: static; flex-basis: 100%; } }
</style>
