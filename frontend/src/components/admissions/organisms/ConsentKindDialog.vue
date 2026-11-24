<template>
  <dialog ref="dialog" class="adm-dialog" aria-labelledby="consent-title" @close="emit('close')">
    <form class="adm-dialog__body" @submit.prevent="submit">
      <div>
        <p class="consent__eyebrow">Einwilligung einfügen</p>
        <h2 id="consent-title">{{ mode === 'new' ? 'Neue Einwilligungsart' : 'Einwilligungsart wählen' }}</h2>
      </div>

      <div v-if="canCreate" class="consent__tabs" role="tablist" aria-label="Quelle">
        <button type="button" role="tab" class="consent__tab" :aria-selected="mode === 'existing'" @click="mode = 'existing'">
          Vorhandene wählen ({{ kinds.length }})
        </button>
        <button type="button" role="tab" class="consent__tab" :aria-selected="mode === 'new'" @click="mode = 'new'">
          Neu anlegen
        </button>
      </div>

      <template v-if="mode === 'existing'">
        <fieldset class="consent__list">
          <legend class="sr-only">Einwilligungsart</legend>
          <label v-for="kind in kinds" :key="kind.slug" class="consent__option" :class="{ 'consent__option--on': chosen === kind.slug }">
            <input v-model="chosen" type="radio" name="consent-kind" :value="kind.slug" class="adm-check" />
            <span>
              <strong>{{ kind.label }}</strong>
              <span v-if="kind.description" class="consent__text">{{ kind.description }}</span>
            </span>
          </label>
          <p v-if="!kinds.length" class="consent__note">Noch keine aktiven Einwilligungsarten.</p>
        </fieldset>
      </template>

      <template v-else>
        <AdmField input-id="consent-label" label="Bezeichnung" required>
          <input id="consent-label" v-model="label" class="adm-input" required maxlength="200" />
        </AdmField>
        <AdmField input-id="consent-text" label="Wortlaut, dem zugestimmt wird" required>
          <textarea id="consent-text" v-model="description" class="adm-input" rows="5" required></textarea>
        </AdmField>
        <label class="consent__check">
          <input v-model="inPortal" type="checkbox" class="adm-check" />
          <span>Im Portal widerrufbar<br /><span class="consent__note">Eltern sehen die Einwilligung je Kind und können sie dort zurückziehen.</span></span>
        </label>
      </template>

      <AdmField input-id="consent-person" label="Gilt für">
        <select id="consent-person" v-model="person" class="adm-input">
          <option value="guardians">Sorgeberechtigte (je Kind)</option>
          <option value="applicant">Antragsteller*in</option>
        </select>
      </AdmField>
      <p v-if="mode === 'new'" class="consent__info">
        Gilt für die ganze Organisation und erscheint auch in den Datenschutz-Einstellungen. Wer den Wortlaut später ändert,
        erzeugt eine neue Version; erteilte Einwilligungen behalten ihre.
      </p>
      <p v-if="mode === 'new' && privacy.kindsError" class="consent__error" role="alert">{{ privacy.kindsError }}</p>

      <div class="adm-dialog__actions">
        <AdmButton variant="ghost" @click="close">Abbrechen</AdmButton>
        <AdmButton variant="primary" type="submit" :loading="privacy.kindsSaving" :disabled="!canSubmit">
          {{ mode === 'new' ? 'Anlegen und einfügen' : 'Einfügen' }}
        </AdmButton>
      </div>
    </form>
  </dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AdmButton from '../atoms/AdmButton.vue'
import AdmField from '../atoms/AdmField.vue'
import { usePrivacyStore } from '@/stores/privacy'
import type { BuilderReferences, ConsentPerson } from '@/types/admissions'
import '../atoms/admInput.css'

interface Props {
  open: boolean
  references: BuilderReferences | null
  canCreate: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'chosen', choice: { slug: string; label: string; person: ConsentPerson; created: boolean }): void
}>()

const privacy = usePrivacyStore()
const dialog = ref<HTMLDialogElement | null>(null)
const mode = ref<'existing' | 'new'>('existing')
const chosen = ref('')
const label = ref('')
const description = ref('')
const inPortal = ref(true)
const person = ref<ConsentPerson>('guardians')

const kinds = computed(() => props.references?.consent_kinds ?? [])
const canSubmit = computed(() =>
  mode.value === 'existing' ? !!chosen.value : !!label.value.trim() && !!description.value.trim()
)

function slugFor(text: string) {
  const base =
    text
      .toLowerCase()
      .replace(/ä/g, 'ae')
      .replace(/ö/g, 'oe')
      .replace(/ü/g, 'ue')
      .replace(/ß/g, 'ss')
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 40) || 'einwilligung'
  const taken = new Set(kinds.value.map((kind) => kind.slug))
  let slug = base
  for (let counter = 2; taken.has(slug); counter++) slug = `${base}_${counter}`
  return slug
}

watch(
  () => props.open,
  (open) => {
    if (!dialog.value) return
    if (!open) return dialog.value.open && dialog.value.close()
    mode.value = kinds.value.length || !props.canCreate ? 'existing' : 'new'
    chosen.value = ''
    label.value = ''
    description.value = ''
    inPortal.value = true
    person.value = 'guardians'
    dialog.value.showModal()
  }
)

function close() {
  dialog.value?.close()
}

async function submit() {
  if (mode.value === 'existing') {
    const kind = kinds.value.find((entry) => entry.slug === chosen.value)
    if (!kind) return
    emit('chosen', { slug: kind.slug, label: kind.label, person: person.value, created: false })
    return close()
  }
  const slug = slugFor(label.value)
  const saved = await privacy.saveConsentKind({
    slug,
    label: label.value.trim(),
    description: description.value.trim(),
    in_portal: inPortal.value,
    active: true,
    position: kinds.value.length
  })
  // On failure privacy.kindsError is shown in the dialog.
  if (!saved) return
  emit('chosen', { slug, label: label.value.trim(), person: person.value, created: true })
  close()
}
</script>

<style scoped>
.adm-dialog {
  width: min(34rem, calc(100vw - 2rem));
  padding: 0;
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
}

.adm-dialog::backdrop {
  background: var(--jf-color-backdrop);
}

.adm-dialog__body {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-3);
}

.adm-dialog__body h2 {
  margin: var(--jf-space-0-5) 0 0;
  font-size: var(--jf-text-lg);
}

.consent__eyebrow {
  margin: 0;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--jf-color-primary);
}

.consent__tabs {
  display: flex;
  gap: var(--jf-space-0-5);
  padding: var(--jf-space-0-5);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
}

.consent__tab {
  flex: 1;
  min-height: 40px;
  border: 0;
  border-radius: var(--jf-radius-md);
  background: none;
  color: var(--jf-color-text);
  font: inherit;
  cursor: pointer;
}

.consent__tab[aria-selected='true'] {
  background: var(--jf-color-card);
  font-weight: var(--jf-weight-semibold);
  box-shadow: var(--jf-shadow-sm);
}

.consent__tab:focus-visible {
  outline: var(--jf-focus-ring);
  outline-offset: 2px;
}

.consent__list {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  max-height: 18rem;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  border: 0;
}

.consent__option {
  display: flex;
  gap: var(--jf-space-1);
  align-items: flex-start;
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  cursor: pointer;
}

.consent__option--on {
  border: 2px solid var(--jf-color-primary);
  background: var(--jf-color-selected);
}

.consent__text {
  display: block;
  margin-top: 0.15rem;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.consent__check {
  display: flex;
  gap: var(--jf-space-1);
  align-items: flex-start;
}

.consent__note {
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.consent__info {
  margin: 0;
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
  font-size: var(--jf-text-sm);
}

.consent__error {
  margin: 0;
  color: var(--jf-color-danger);
}

.adm-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--jf-space-1);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
