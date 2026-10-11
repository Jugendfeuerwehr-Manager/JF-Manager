<template>
  <fieldset class="slot-editor" :disabled="readonly || disabled" aria-describedby="slot-editor-hint">
    <legend class="slot-editor__title">Positionen und Mindestbesetzung</legend>
    <p id="slot-editor-hint" class="slot-hint">
      <template v-if="disabled"><i class="pi pi-lock" aria-hidden="true"></i>Positionen gibt es nur bei Anmeldung oder Zuteilung.</template>
      <template v-else>Benannte Funktionen mit Mindestzahl (für die Mindestbesetzung) und Plätzen. Ohne Positionen gilt nur die Höchstzahl.</template>
    </p>

    <p v-if="error('slots')" class="slot-error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ error('slots') }}</p>

    <ol v-if="slots.length" class="slot-list">
      <li v-for="(slot, index) in slots" :key="slot.key" class="slot-row" :data-slot-row="index">
        <div class="slot-row__fields">
          <div class="slot-field slot-field--label">
            <label :for="`slot-${index}-label`">Bezeichnung</label>
            <input :id="`slot-${index}-label`" v-model="slot.label" class="slot-input" maxlength="80" placeholder="z. B. Wachführung" :aria-invalid="!!error(`slots[${index}].label`)">
            <span v-if="error(`slots[${index}].label`)" class="slot-error" role="alert">{{ error(`slots[${index}].label`) }}</span>
          </div>
          <div class="slot-field">
            <label :for="`slot-${index}-min`">Mindestens</label>
            <input :id="`slot-${index}-min`" v-model.number="slot.min" type="number" min="0" :max="slot.max" class="slot-input" :aria-invalid="!!error(`slots[${index}].min`)">
            <span v-if="error(`slots[${index}].min`)" class="slot-error" role="alert">{{ error(`slots[${index}].min`) }}</span>
          </div>
          <div class="slot-field">
            <label :for="`slot-${index}-max`">Plätze</label>
            <input :id="`slot-${index}-max`" v-model.number="slot.max" type="number" min="1" class="slot-input" :aria-invalid="!!error(`slots[${index}].max`)">
            <span v-if="error(`slots[${index}].max`)" class="slot-error" role="alert">{{ error(`slots[${index}].max`) }}</span>
          </div>
          <div class="slot-row__actions" role="group" :aria-label="`Position ${slot.label || index + 1}`">
            <Button icon="pi pi-arrow-up" text severity="secondary" :aria-label="`${slot.label || 'Position'} nach oben`" :disabled="index === 0" @click="store.moveSlot(index, -1)" />
            <Button icon="pi pi-arrow-down" text severity="secondary" :aria-label="`${slot.label || 'Position'} nach unten`" :disabled="index === slots.length - 1" @click="store.moveSlot(index, 1)" />
            <Button icon="pi pi-trash" text severity="danger" :aria-label="`${slot.label || 'Position'} entfernen`" @click="store.removeSlot(index)" />
          </div>
        </div>
        <p v-if="staffingRow(slot.id)" class="slot-hint">
          Besetzt: {{ staffingRow(slot.id)!.seated }} von {{ staffingRow(slot.id)!.max }}<template v-if="staffingRow(slot.id)!.missing"> · es fehlen {{ staffingRow(slot.id)!.missing }}</template>
        </p>
        <details class="slot-rule" :open="slot.rule.rules.length > 0 || hasRuleError(index)">
          <summary>Voraussetzung der Position <span class="slot-hint">({{ slot.rule.rules.length ? `${slot.rule.rules.length} Bedingung${slot.rule.rules.length === 1 ? '' : 'en'}` : 'keine zusätzliche' }})</span></summary>
          <RuleBuilder
            v-model="slot.rule"
            :uid="`slot-${index}-rule`"
            :errors="ruleErrors(index)"
            :options="options"
            :loading="optionsLoading"
          />
        </details>
      </li>
    </ol>

    <div class="slot-editor__footer">
      <Button label="Position hinzufügen" icon="pi pi-plus" severity="secondary" outlined :disabled="readonly || disabled" @click="store.addSlot()" />
      <div v-if="slots.length" class="slot-field slot-field--extra">
        <label for="slot-extra">Weitere Plätze ohne Position</label>
        <input id="slot-extra" type="number" min="0" class="slot-input" :value="extraPlaces ?? ''" placeholder="keine" aria-describedby="slot-extra-hint" @input="setExtra">
        <span id="slot-extra-hint" class="slot-hint">z. B. Hospitierende</span>
      </div>
    </div>
    <p v-if="slots.length" class="slot-summary" role="status">
      <i class="pi pi-users" aria-hidden="true"></i>Plätze gesamt: <strong>{{ capacity }}</strong> (aus den Positionen abgeleitet)
    </p>
    <p v-if="staffing && staffing.required" class="slot-summary" :class="staffing.met ? 'slot-summary--ok' : 'slot-summary--warn'">
      <i :class="staffing.met ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'" aria-hidden="true"></i>{{ staffing.text }}
    </p>
  </fieldset>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import RuleBuilder from './RuleBuilder.vue'
import type { RuleOption } from '@/composables/useRuleOptions'
import { draftCapacity, useParticipationStore } from '@/stores/participation'
import type { RuleErrors } from '@/api/participation'

defineProps<{ readonly?: boolean, disabled?: boolean, options: Record<string, RuleOption[]>, optionsLoading?: boolean }>()
const store = useParticipationStore()

const slots = computed(() => store.draft?.slots ?? [])
const extraPlaces = computed(() => store.draft?.extra_places ?? null)
const capacity = computed(() => (store.draft ? draftCapacity(store.draft) : null))
const staffing = computed(() => store.config?.staffing ?? null)

const error = (key: string) => store.fieldErrors[key]
const staffingRow = (id: number | null) => (id === null ? null : staffing.value?.slots.find(row => row.id === id) ?? null)

function ruleErrors(index: number): RuleErrors {
  const prefix = `slots[${index}].rule.`
  const out: RuleErrors = {}
  for (const [key, message] of Object.entries(store.fieldErrors)) {
    if (key.startsWith(prefix)) out[key.slice(prefix.length)] = message
  }
  return out
}
const hasRuleError = (index: number) => Object.keys(ruleErrors(index)).length > 0

function setExtra(event: Event) {
  if (!store.draft) return
  const raw = (event.target as HTMLInputElement).value
  store.draft.extra_places = raw === '' ? null : Number(raw)
}
</script>

<style scoped>
.slot-editor { display: grid; gap: var(--jf-space-1-5); margin: 0; padding: var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-card); min-width: 0; }
.slot-editor__title { margin: 0; padding: 0 var(--jf-space-0-5); font-size: var(--jf-text-lg); font-weight: var(--jf-weight-bold); }
.slot-list { margin: 0; padding: 0; list-style: none; display: grid; gap: var(--jf-space-1-5); }
.slot-row { display: grid; gap: var(--jf-space-1); padding: var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); }
.slot-row__fields { display: flex; flex-wrap: wrap; gap: var(--jf-space-1-5); align-items: flex-end; }
.slot-field { display: grid; gap: var(--jf-space-0-5); flex: 1 1 6rem; min-width: 0; }
.slot-field--label { flex: 3 1 12rem; }
.slot-field--extra { flex: 0 1 14rem; }
.slot-field > label { font-weight: var(--jf-weight-semibold); font-size: var(--jf-text-sm); }
.slot-input { min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-sm); background: var(--jf-color-card); color: var(--jf-color-text); font: inherit; box-sizing: border-box; width: 100%; }
.slot-input[aria-invalid='true'] { border-color: var(--p-red-600); }
.slot-row__actions { display: flex; gap: 2px; }
.slot-row__actions :deep(.p-button) { min-width: var(--jf-touch-target); min-height: var(--jf-touch-target); }
.slot-rule summary { min-height: var(--jf-touch-target); display: flex; align-items: center; gap: var(--jf-space-0-5); cursor: pointer; font-weight: var(--jf-weight-semibold); }
.slot-editor__footer { display: flex; flex-wrap: wrap; gap: var(--jf-space-2); align-items: flex-end; justify-content: space-between; }
.slot-hint { margin: 0; color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); font-weight: normal; }
.slot-hint i, .slot-error i, .slot-summary i { margin-right: var(--jf-space-0-5); }
.slot-error { margin: 0; color: var(--p-red-600); font-size: var(--jf-text-sm); }
.slot-summary { margin: 0; display: flex; align-items: center; gap: var(--jf-space-0-5); }
.slot-summary--warn { color: var(--p-amber-700); }
.slot-summary--ok { color: var(--p-green-700); }
.app-dark .slot-error { color: var(--p-red-300); }
.app-dark .slot-summary--warn { color: var(--p-amber-300); }
.app-dark .slot-summary--ok { color: var(--p-green-300); }
</style>
