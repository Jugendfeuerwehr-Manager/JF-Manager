<template>
  <fieldset class="props" :disabled="readonly">
    <legend class="sr-only">Eigenschaften: {{ ELEMENT_LABELS[element.type] }}</legend>
    <div class="props__grid">
      <AdmField v-if="hasLabel" :input-id="id('label')" :label="element.type === 'heading' ? 'Text' : 'Beschriftung'">
        <input :id="id('label')" class="adm-input" :value="element.label ?? ''" @input="patch({ label: value($event) })" />
      </AdmField>
      <AdmField v-if="hasHelp" :input-id="id('help')" label="Hilfetext">
        <input
          :id="id('help')"
          class="adm-input"
          placeholder="Optional, erscheint unter dem Feld"
          :value="element.help ?? ''"
          @input="patch({ help: value($event) })"
        />
      </AdmField>

      <template v-if="element.type === 'richtext'">
        <AdmField :input-id="id('block')" label="Textbaustein">
          <select :id="id('block')" class="adm-input" :value="element.text_block ?? ''" @change="setTextBlock(value($event))">
            <option value="">Eigener Text</option>
            <option v-for="block in textBlocks" :key="block.id" :value="block.id">{{ block.title }}</option>
          </select>
        </AdmField>
        <AdmField
          v-if="!element.text_block"
          class="props__wide"
          :input-id="id('html')"
          label="Text"
          hint="Absätze mit <p>, Listen mit <ul>/<ol>, Hervorhebung mit <strong>. Wird beim Speichern bereinigt."
        >
          <textarea :id="id('html')" class="adm-input prop-code" :value="element.html ?? ''" @input="patch({ html: value($event) })"></textarea>
        </AdmField>
      </template>

      <label v-if="hasRequired" class="props__check">
        <input type="checkbox" class="adm-check" :checked="!!element.required" @change="patch({ required: checked($event) })" />
        Pflichtangabe
      </label>

      <AdmField v-if="!isContentType" :input-id="id('visibility')" label="Sichtbar">
        <select :id="id('visibility')" class="adm-input" :value="visibilityMode" @change="setVisibilityMode(value($event))">
          <option value="always">Immer</option>
          <option value="age">Nur unter einem Alter</option>
          <option value="field" :disabled="!earlierKeys.length">Wenn ein vorheriges Feld einen Wert hat</option>
        </select>
      </AdmField>
      <AdmField v-if="visibilityMode === 'age'" :input-id="id('age')" label="Jünger als (Jahre)">
        <input :id="id('age')" type="number" min="1" max="120" class="adm-input" :value="ageBelow" @input="patch({ visible_if: { age_below: number($event) } })" />
      </AdmField>
      <template v-if="visibilityMode === 'field'">
        <AdmField :input-id="id('vfield')" label="Feld">
          <select :id="id('vfield')" class="adm-input" :value="ruleField" @change="patch({ visible_if: { field: value($event), equals: ruleEquals } })">
            <option v-for="key in earlierKeys" :key="key" :value="key">{{ key }}</option>
          </select>
        </AdmField>
        <AdmField :input-id="id('vvalue')" label="Wert" hint="Bei Ankreuzfeldern: ja">
          <input :id="id('vvalue')" class="adm-input" :value="String(ruleEquals)" @input="setRuleValue(value($event))" />
        </AdmField>
      </template>

      <p v-if="element.target" class="props__info props__wide">
        Wird bei der Übernahme in <strong>{{ targetLabel(element.target, references) }}</strong> geschrieben.
        <template v-if="element.target === 'member.birthday'"> Steuert auch das Alter für die Sichtbarkeitsregeln.</template>
        <template v-if="element.target === 'member.health_notes'"> Gesundheitsdaten: nur mit eigenem Recht lesbar.</template>
      </p>
      <AdmField
        v-else-if="needsTarget"
        class="props__wide"
        :input-id="id('target')"
        label="Übernehmen in"
        hint="Ohne Ziel ginge die Angabe bei der Übernahme verloren. Passt nichts, lege ein Zusatzfeld an."
      >
        <select :id="id('target')" class="adm-input" value="" @change="setTarget(value($event))">
          <option value="" disabled>Bitte wählen</option>
          <option v-for="field in targets" :key="field.key" :value="field.key">{{ targetLabel(field.key, references) }}</option>
        </select>
      </AdmField>
      <p v-else-if="element.type === 'checkbox' && !element.target" class="props__info props__wide">
        Bestätigung: steht nur im versiegelten Antrag, nicht am Mitglied. Deshalb immer eine Pflichtangabe.
      </p>

      <section v-if="hasOptions" class="props__group props__wide">
        <h4>Möglichkeiten</h4>
        <div v-for="(option, index) in element.options ?? []" :key="index" class="props__option">
          <input
            class="adm-input"
            :aria-label="`Möglichkeit ${index + 1}`"
            :value="option.label"
            @input="setOption(index, { label: value($event), value: option.value || slug(value($event)) })"
          />
          <AdmButton variant="danger" icon="pi pi-times" :aria-label="`Möglichkeit ${index + 1} entfernen`" @click="removeOption(index)" />
        </div>
        <AdmButton icon="pi pi-plus" @click="addOption">Möglichkeit</AdmButton>
      </section>
      <p v-else-if="extraOptions" class="props__info props__wide">
        Möglichkeiten kommen aus dem Zusatzfeld: {{ extraOptions }}
      </p>

      <AdmField v-if="element.type === 'legal_ack'" :input-id="id('legal')" label="Rechtstext">
        <select :id="id('legal')" class="adm-input" :value="element.legal_kind ?? ''" @change="patch({ legal_kind: value($event) })">
          <option v-for="kind in references?.legal_kinds ?? []" :key="kind.value" :value="kind.value">{{ kind.label }}</option>
        </select>
      </AdmField>

      <template v-if="element.type === 'consent'">
        <AdmField :input-id="id('consent')" label="Einwilligungsart">
          <select :id="id('consent')" class="adm-input" :value="element.consent_kind ?? ''" @change="setConsentKind(value($event))">
            <option value="" disabled>Bitte wählen</option>
            <option v-for="kind in references?.consent_kinds ?? []" :key="kind.slug" :value="kind.slug">{{ kind.label }}</option>
          </select>
        </AdmField>
        <AdmField :input-id="id('person')" label="Erklärt von">
          <select :id="id('person')" class="adm-input" :value="element.person ?? 'applicant'" @change="patch({ person: value($event) as ConsentPerson })">
            <option value="applicant">Antragsteller*in</option>
            <option value="guardians">Sorgeberechtigte</option>
          </select>
        </AdmField>
        <p v-if="consentText" class="props__quote props__wide">{{ consentText }}</p>
        <div v-if="canCreateConsent" class="props__wide">
          <AdmButton variant="ghost" icon="pi pi-plus" @click="emit('create-consent')">Neue Einwilligungsart anlegen</AdmButton>
        </div>
      </template>

      <AdmField v-if="element.type === 'signature'" :input-id="id('role')" label="Unterschreibt">
        <select :id="id('role')" class="adm-input" :value="element.role ?? 'applicant'" @change="patch({ role: value($event) as SignatureRole })">
          <option v-for="(label, role) in SIGNATURE_ROLE_LABELS" :key="role" :value="role">{{ label }}</option>
        </select>
      </AdmField>

      <section v-if="element.type === 'guardians'" class="props__group props__wide">
        <h4>Sorgeberechtigte</h4>
        <div class="props__row">
          <AdmField :input-id="id('min')" label="Mindestens">
            <input :id="id('min')" type="number" min="0" max="4" class="adm-input" :value="element.min ?? 1" @input="patch({ min: number($event) })" />
          </AdmField>
          <AdmField :input-id="id('max')" label="Höchstens">
            <input :id="id('max')" type="number" min="1" max="4" class="adm-input" :value="element.max ?? 2" @input="patch({ max: number($event) })" />
          </AdmField>
        </div>
        <table class="props__table">
          <thead>
            <tr><th scope="col">Feld</th><th scope="col">Abfragen</th><th scope="col">Pflicht</th></tr>
          </thead>
          <tbody>
            <tr v-for="field in references?.fields.guardian ?? []" :key="field.key">
              <th scope="row">{{ field.label }}</th>
              <td>
                <input
                  type="checkbox"
                  class="adm-check"
                  :aria-label="`${field.label} abfragen`"
                  :checked="guardianField(field.key) !== undefined"
                  :disabled="isNameField(field.key)"
                  @change="toggleGuardianField(field.key, checked($event))"
                />
              </td>
              <td>
                <input
                  type="checkbox"
                  class="adm-check"
                  :aria-label="`${field.label} Pflicht`"
                  :checked="!!guardianField(field.key)?.required"
                  :disabled="guardianField(field.key) === undefined"
                  @change="setGuardianRequired(field.key, checked($event))"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <details v-if="hasKey" class="props__advanced props__wide">
        <summary>Erweitert</summary>
        <AdmField :input-id="id('key')" label="Kennung" hint="Interner Name der Antwort (Kleinbuchstaben, Ziffern, _).">
          <input :id="id('key')" class="adm-input prop-code" :value="element.key ?? ''" @input="patch({ key: slug(value($event)) })" />
        </AdmField>
      </details>
    </div>

    <footer class="props__footer">
      <div class="props__footer-group">
        <AdmButton icon="pi pi-arrow-up" aria-label="Nach oben" :disabled="first" @click="emit('move', -1)" />
        <AdmButton icon="pi pi-arrow-down" aria-label="Nach unten" :disabled="last" @click="emit('move', 1)" />
        <AdmButton v-if="canDuplicate" icon="pi pi-copy" aria-label="Duplizieren" @click="emit('duplicate')" />
        <AdmButton variant="danger" icon="pi pi-trash" @click="emit('remove')">Entfernen</AdmButton>
      </div>
      <AdmButton variant="primary" icon="pi pi-check" @click="emit('done')">Fertig</AdmButton>
    </footer>
  </fieldset>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AdmButton from '../atoms/AdmButton.vue'
import AdmField from '../atoms/AdmField.vue'
import type {
  AdmissionTextBlock,
  BuilderReferences,
  ConsentPerson,
  FormElement,
  GuardianFieldConfig,
  SignatureRole
} from '@/types/admissions'
import { ELEMENT_LABELS, SIGNATURE_ROLE_LABELS, isContent, targetLabel } from '@/utils/admissionSchema'
import '../atoms/admInput.css'

interface Props {
  element: FormElement
  references: BuilderReferences | null
  textBlocks: AdmissionTextBlock[]
  /** answer keys of elements placed before this one */
  earlierKeys: string[]
  /** targets other elements already fill */
  usedTargets: Set<string>
  first?: boolean
  last?: boolean
  readonly?: boolean
  canCreateConsent?: boolean
}

const props = withDefaults(defineProps<Props>(), { first: false, last: false, readonly: false, canCreateConsent: false })
const emit = defineEmits<{
  (e: 'update', patch: Partial<FormElement>): void
  (e: 'remove'): void
  (e: 'duplicate'): void
  (e: 'move', step: -1 | 1): void
  (e: 'done'): void
  (e: 'create-consent'): void
}>()

const SINGLE_USE = ['guardians', 'legal_ack', 'signature']
const INPUTS = ['text', 'textarea', 'number', 'date', 'email', 'phone', 'select', 'radio', 'checkbox', 'photo']

const id = (name: string) => `prop-${props.element.id}-${name}`
const isContentType = computed(() => isContent(props.element.type))
const hasKey = computed(() => !isContentType.value)
const hasLabel = computed(() => !['richtext', 'divider'].includes(props.element.type))
const hasHelp = computed(() => !isContentType.value && !['signature', 'guardians', 'legal_ack', 'consent'].includes(props.element.type))
const hasRequired = computed(() => INPUTS.includes(props.element.type) || ['legal_ack', 'consent', 'signature'].includes(props.element.type))
const isExtraTarget = computed(() => (props.element.target ?? '').startsWith('member.extra.'))
const hasOptions = computed(
  () => ['select', 'radio'].includes(props.element.type) && props.element.target !== 'member.gender' && !isExtraTarget.value
)
const extraOptions = computed(() =>
  isExtraTarget.value && props.element.type === 'select'
    ? (props.element.options ?? []).map((option) => option.label).join(', ')
    : ''
)
const canDuplicate = computed(() => !props.element.target && !SINGLE_USE.includes(props.element.type))
// Old drafts may hold inputs without a destination; confirmations (checkboxes) are fine without.
const needsTarget = computed(
  () => INPUTS.includes(props.element.type) && !props.element.target && props.element.type !== 'checkbox'
)
const targets = computed(() => {
  const fields = [...(props.references?.fields.member ?? []), ...(props.references?.fields.extra ?? [])]
  return fields.filter(
    (field) =>
      !props.usedTargets.has(field.key) &&
      (field.input_type === props.element.type || (field.input_type === 'text' && props.element.type === 'textarea'))
  )
})
const consentText = computed(
  () => props.references?.consent_kinds.find((kind) => kind.slug === props.element.consent_kind)?.description ?? ''
)

const visibilityMode = computed(() => {
  const rule = props.element.visible_if
  if (!rule) return 'always'
  return 'age_below' in rule ? 'age' : 'field'
})
const ageBelow = computed(() => {
  const rule = props.element.visible_if
  return rule && 'age_below' in rule ? rule.age_below : 18
})
const ruleField = computed(() => {
  const rule = props.element.visible_if
  return rule && 'field' in rule ? rule.field : ''
})
const ruleEquals = computed(() => {
  const rule = props.element.visible_if
  return rule && 'field' in rule ? rule.equals : true
})

const value = (event: Event) => (event.target as HTMLInputElement).value
const checked = (event: Event) => (event.target as HTMLInputElement).checked
const number = (event: Event) => Number.parseInt(value(event), 10) || 0
const slug = (text: string) =>
  text
    .toLowerCase()
    .replace(/ä/g, 'ae')
    .replace(/ö/g, 'oe')
    .replace(/ü/g, 'ue')
    .replace(/ß/g, 'ss')
    .replace(/[^a-z0-9_]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 50)

function patch(change: Partial<FormElement>) {
  emit('update', change)
}

function setTarget(target: string) {
  const extra = props.references?.fields.extra.find((field) => field.key === target)
  patch({ target, options: extra ? extra.options.map((option) => ({ value: option, label: option })) : props.element.options })
}

function setTextBlock(raw: string) {
  patch({ text_block: raw ? Number(raw) : null })
}

function setConsentKind(slugValue: string) {
  const kind = props.references?.consent_kinds.find((entry) => entry.slug === slugValue)
  const label = props.element.label && props.element.label !== ELEMENT_LABELS.consent ? props.element.label : kind?.label
  patch({ consent_kind: slugValue, label })
}

function setOption(index: number, option: { value: string; label: string }) {
  const options = [...(props.element.options ?? [])]
  options[index] = option
  patch({ options })
}

function addOption() {
  const options = props.element.options ?? []
  patch({ options: [...options, { value: `option_${options.length + 1}`, label: `Möglichkeit ${options.length + 1}` }] })
}

function removeOption(index: number) {
  patch({ options: (props.element.options ?? []).filter((_, position) => position !== index) })
}

function isNameField(target: string) {
  return target === 'guardian.name' || target === 'guardian.lastname'
}

function guardianField(target: string): GuardianFieldConfig | undefined {
  return props.element.fields?.find((field) => field.target === target)
}

function toggleGuardianField(target: string, on: boolean) {
  const fields = props.element.fields ?? []
  patch({ fields: on ? [...fields, { target, required: false }] : fields.filter((field) => field.target !== target) })
}

function setGuardianRequired(target: string, required: boolean) {
  patch({ fields: (props.element.fields ?? []).map((field) => (field.target === target ? { ...field, required } : field)) })
}

function setVisibilityMode(mode: string) {
  if (mode === 'always') return patch({ visible_if: null })
  if (mode === 'age') return patch({ visible_if: { age_below: 18 } })
  patch({ visible_if: { field: props.earlierKeys[0] ?? '', equals: true } })
}

function setRuleValue(raw: string) {
  const equals = raw === 'ja' ? true : raw === 'nein' ? false : raw
  patch({ visible_if: { field: ruleField.value, equals } })
}
</script>

<style scoped>
.props {
  margin: 0;
  padding: 0;
  border: 0;
  min-width: 0;
}

.props__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-2);
}

.props__wide {
  grid-column: 1 / -1;
}

.props__group {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
}

.props__group h4 {
  margin: 0;
  font-size: var(--jf-text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--jf-color-text-muted);
}

.props__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--jf-space-1);
}

.props__option {
  display: flex;
  gap: var(--jf-space-0-5);
}

.props__check {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target, 44px);
  align-self: end;
}

.props__info {
  margin: 0;
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
  font-size: var(--jf-text-sm);
}

.props__quote {
  margin: 0;
  padding: var(--jf-space-1);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.props__table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--jf-text-sm);
}

.props__table th,
.props__table td {
  padding: 0.25rem;
  text-align: left;
}

.props__table th[scope='row'] {
  font-weight: normal;
}

.props__advanced summary {
  min-height: var(--jf-touch-target, 44px);
  display: flex;
  align-items: center;
  cursor: pointer;
  color: var(--jf-color-text-muted);
}

.props__footer {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: var(--jf-space-1);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border-top: 1px solid var(--jf-color-border);
}

.props__footer-group {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-0-5);
}

.prop-code {
  font-family: var(--jf-font-mono);
  font-size: var(--jf-text-sm);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

@media (max-width: 640px) {
  .props__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
