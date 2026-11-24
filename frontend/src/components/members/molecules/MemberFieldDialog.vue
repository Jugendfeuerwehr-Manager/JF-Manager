<template>
  <dialog ref="dialog" class="mf-dialog" aria-labelledby="mf-title" @close="emit('close')">
    <form class="mf-dialog__body" @submit.prevent="submit">
      <div>
        <p class="mf-dialog__eyebrow">Zusatzfeld am Mitglied</p>
        <h2 id="mf-title">Neues Zusatzfeld</h2>
        <p class="mf-dialog__lead">
          Die Angabe wird am Mitglied gespeichert und erscheint in der Mitgliedsbearbeitung unter „Zusatzangaben“.
        </p>
      </div>

      <label class="mf-field">
        <span>Bezeichnung</span>
        <input v-model="label" class="mf-input" required maxlength="100" autocomplete="off" />
      </label>

      <fieldset class="mf-types">
        <legend>Art der Angabe</legend>
        <div class="mf-types__grid">
          <button
            v-for="option in TYPE_OPTIONS"
            :key="option.value"
            type="button"
            class="mf-type"
            :aria-pressed="fieldType === option.value"
            @click="fieldType = option.value"
          >
            {{ option.label }}
          </button>
        </div>
      </fieldset>

      <label v-if="fieldType === 'select'" class="mf-field">
        <span>Möglichkeiten, eine pro Zeile</span>
        <textarea v-model="optionsText" class="mf-input" rows="4" required></textarea>
      </label>

      <label v-if="scopes.length > 1" class="mf-field">
        <span>Gilt für</span>
        <select v-model="department" class="mf-input">
          <option v-for="scope in scopes" :key="String(scope.id)" :value="scope.id">{{ scope.name }}</option>
        </select>
      </label>
      <p v-else-if="scopes.length" class="mf-note">Gilt für: {{ scopes[0]!.name }}</p>

      <p class="mf-note">
        Gesundheitsangaben gehören nicht hierher: Dafür gibt es das geschützte Feld „Gesundheit“ mit eigenem Zugriffsrecht.
      </p>
      <p v-if="store.error" class="mf-error" role="alert">{{ store.error }}</p>

      <div class="mf-dialog__actions">
        <button type="button" class="mf-button" @click="close">Abbrechen</button>
        <button type="submit" class="mf-button mf-button--primary" :disabled="store.saving || !label.trim()">
          {{ submitLabel }}
        </button>
      </div>
    </form>
  </dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useMemberFieldsStore } from '@/stores/memberFields'
import type { MemberFieldDefinition, MemberFieldType } from '@/types/members'

interface Scope {
  id: number | null
  name: string
}

interface Props {
  open: boolean
  /** Where the field may live; ``id: null`` is the whole organisation. */
  scopes: Scope[]
  submitLabel?: string
}

const props = withDefaults(defineProps<Props>(), { submitLabel: 'Anlegen' })
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', definition: MemberFieldDefinition): void
}>()

const TYPE_OPTIONS: { value: MemberFieldType; label: string }[] = [
  { value: 'text', label: 'Text' },
  { value: 'textarea', label: 'Mehrzeilig' },
  { value: 'number', label: 'Zahl' },
  { value: 'date', label: 'Datum' },
  { value: 'select', label: 'Auswahl' },
  { value: 'checkbox', label: 'Ja / Nein' }
]

const store = useMemberFieldsStore()
const dialog = ref<HTMLDialogElement | null>(null)
const label = ref('')
const fieldType = ref<MemberFieldType>('text')
const optionsText = ref('')
const department = ref<number | null>(null)

const options = computed(() =>
  optionsText.value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
)

function reset() {
  label.value = ''
  fieldType.value = 'text'
  optionsText.value = ''
  department.value = props.scopes[0]?.id ?? null
  store.clearError()
}

watch(
  () => props.open,
  (open) => {
    if (!dialog.value) return
    if (!open) return dialog.value.open && dialog.value.close()
    reset()
    dialog.value.showModal()
  }
)

function close() {
  dialog.value?.close()
}

async function submit() {
  try {
    const definition = await store.save({
      label: label.value.trim(),
      field_type: fieldType.value,
      options: fieldType.value === 'select' ? options.value : [],
      department: department.value,
      help_text: ''
    })
    emit('created', definition)
    close()
  } catch {
    // store.error is shown in the dialog
  }
}
</script>

<style scoped>
.mf-dialog {
  width: min(32rem, calc(100vw - 2rem));
  padding: 0;
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
}

.mf-dialog::backdrop {
  background: var(--jf-color-backdrop);
}

.mf-dialog__body {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  padding: var(--jf-space-3);
}

.mf-dialog__eyebrow {
  margin: 0;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--jf-color-primary);
}

.mf-dialog h2 {
  margin: var(--jf-space-0-5) 0 0;
  font-size: var(--jf-text-lg);
}

.mf-dialog__lead,
.mf-note {
  margin: var(--jf-space-0-5) 0 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.mf-field {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  font-weight: var(--jf-weight-semibold);
}

.mf-input {
  min-height: var(--jf-touch-target, 44px);
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
  font-weight: normal;
}

.mf-input:focus-visible,
.mf-type:focus-visible,
.mf-button:focus-visible {
  outline: var(--jf-focus-ring);
  outline-offset: 2px;
}

.mf-types {
  margin: 0;
  padding: 0;
  border: 0;
}

.mf-types legend {
  margin-bottom: var(--jf-space-0-5);
  font-weight: var(--jf-weight-semibold);
}

.mf-types__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--jf-space-0-5);
}

.mf-type {
  min-height: var(--jf-touch-target, 44px);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
  cursor: pointer;
}

.mf-type[aria-pressed='true'] {
  border: 2px solid var(--jf-color-primary);
  background: var(--jf-color-selected);
  color: var(--jf-color-selected-text);
  font-weight: var(--jf-weight-semibold);
}

.mf-error {
  margin: 0;
  color: var(--jf-color-danger);
}

.mf-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--jf-space-1);
}

.mf-button {
  min-height: var(--jf-touch-target, 44px);
  padding: 0 var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
  cursor: pointer;
}

.mf-button--primary {
  border-color: var(--jf-color-primary);
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
  font-weight: var(--jf-weight-semibold);
}

.mf-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

@media (max-width: 480px) {
  .mf-types__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
