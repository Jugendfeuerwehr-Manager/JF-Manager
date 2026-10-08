<template>
  <section class="rule-preview" aria-labelledby="rule-preview-title" aria-live="polite">
    <h3 id="rule-preview-title" class="rule-preview__title">Live-Vorschau</h3>
    <p v-if="hasErrors" class="rule-preview__note">
      <i class="pi pi-info-circle" aria-hidden="true"></i>Die Vorschau erscheint, sobald alle Bedingungen gültig sind.
    </p>
    <p v-else-if="error" class="rule-preview__note" role="alert"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i>{{ error }}</p>
    <template v-if="preview && !hasErrors">
      <p class="rule-preview__count" aria-hidden="true">
        <strong class="rule-preview__big">{{ preview.eligible }}</strong>
        <span> von {{ preview.total }}</span>
        <span v-if="loading" class="rule-preview__loading" role="status"><i class="pi pi-spin pi-spinner" aria-hidden="true"></i> aktualisiert …</span>
      </p>
      <p class="rule-preview__text">
        {{ preview.eligible }} von {{ preview.total }} Personen der Zielgruppe erfüllen die Voraussetzungen.
      </p>
      <p v-if="preview.total === 0" class="rule-preview__note">
        <i class="pi pi-exclamation-triangle" aria-hidden="true"></i>Die Zielgruppe ist leer. Bitte Gruppen oder Abteilung des Dienstes prüfen.
      </p>
      <p v-else-if="preview.eligible === 0" class="rule-preview__note">
        <i class="pi pi-exclamation-triangle" aria-hidden="true"></i>Niemand erfüllt diese Voraussetzungen. Mit weniger oder weiteren Bedingungen („mindestens eine“) kommen mehr Personen infrage.
      </p>
      <p v-if="preview.audience_notice" class="rule-preview__muted">Im Portal angezeigt: {{ preview.audience_notice }}</p>
      <details v-if="preview.excluded.length" class="rule-preview__excluded">
        <summary>Ausgeschlossen ({{ preview.excluded.length }})</summary>
        <ul>
          <li v-for="person in preview.excluded" :key="person.member_id">
            <span class="rule-preview__name">{{ person.name }}</span>
            <span class="rule-preview__muted">{{ person.reasons.join('; ') }}</span>
          </li>
        </ul>
      </details>
    </template>
    <p v-else-if="loading && !hasErrors" class="rule-preview__muted" role="status"><i class="pi pi-spin pi-spinner" aria-hidden="true"></i> Vorschau wird berechnet …</p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RuleErrors, RulePreviewResult } from '@/api/participation'

const props = defineProps<{
  preview: RulePreviewResult | null
  loading?: boolean
  error?: string | null
  errors?: RuleErrors
}>()
const hasErrors = computed(() => Object.keys(props.errors ?? {}).length > 0)
</script>

<style scoped>
.rule-preview { display: grid; gap: var(--jf-space-1-5); padding: var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-card); }
.rule-preview__title { margin: 0; font-size: var(--jf-text-lg); }
.rule-preview p { margin: 0; }
.rule-preview__count { display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--jf-space-1); color: var(--jf-color-text-muted); }
.rule-preview__big { font-size: var(--jf-text-2xl); color: var(--jf-color-text); }
.rule-preview__note { display: flex; gap: var(--jf-space-1); padding: var(--jf-space-1) var(--jf-space-1-5); border-radius: var(--jf-radius-md); background: var(--jf-color-ground); font-size: var(--jf-text-sm); }
.rule-preview__muted, .rule-preview__loading { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.rule-preview__excluded summary { min-height: var(--jf-touch-target); display: flex; align-items: center; cursor: pointer; font-weight: var(--jf-weight-semibold); }
.rule-preview__excluded ul { margin: 0; padding: 0; list-style: none; display: grid; gap: var(--jf-space-1); max-height: 20rem; overflow-y: auto; }
.rule-preview__excluded li { display: grid; gap: 2px; }
.rule-preview__name { font-weight: var(--jf-weight-semibold); }
</style>
