<template>
  <aside class="props" aria-label="Eigenschaften">
    <template v-if="element">
      <header class="props__head">
        <h3>{{ ELEMENT_LABELS[element.type] }}</h3>
        <span class="props__actions">
          <AdmButton variant="ghost" icon="pi pi-copy" aria-label="Duplizieren" :disabled="readonly" @click="emit('duplicate')" />
          <AdmButton variant="danger" icon="pi pi-trash" aria-label="Entfernen" :disabled="readonly" @click="emit('remove')" />
        </span>
      </header>

      <fieldset class="props__body" :disabled="readonly">
        <AdmField v-if="hasLabel" input-id="prop-label" label="Beschriftung">
          <input id="prop-label" class="adm-input" :value="element.label ?? ''" @input="patch({ label: value($event) })" />
        </AdmField>

        <AdmField v-if="element.type === 'richtext'" input-id="prop-block" label="Textbaustein">
          <select id="prop-block" class="adm-input" :value="element.text_block ?? ''" @change="setTextBlock(value($event))">
            <option value="">Eigener Text</option>
            <option v-for="block in textBlocks" :key="block.id" :value="block.id">{{ block.title }}</option>
          </select>
        </AdmField>
        <AdmField
          v-if="element.type === 'richtext' && !element.text_block"
          input-id="prop-html"
          label="Text"
          hint="Absätze mit <p>, Listen mit <ul>/<ol>, Hervorhebung mit <strong>. Wird beim Speichern bereinigt."
        >
          <textarea id="prop-html" class="adm-input prop-code" :value="element.html ?? ''" @input="patch({ html: value($event) })"></textarea>
        </AdmField>

        <template v-if="hasKey">
          <AdmField
            input-id="prop-key"
            label="Kennung"
            hint="Interner Name der Antwort (Kleinbuchstaben, Ziffern, _)."
          >
            <input id="prop-key" class="adm-input prop-code" :value="element.key ?? ''" @input="patch({ key: slug(value($event)) })" />
          </AdmField>
          <AdmField v-if="hasHelp" input-id="prop-help" label="Hilfetext">
            <input id="prop-help" class="adm-input" :value="element.help ?? ''" @input="patch({ help: value($event) })" />
          </AdmField>
          <label class="props__check">
            <input type="checkbox" class="adm-check" :checked="!!element.required" @change="patch({ required: checked($event) })" />
            Pflichtangabe
          </label>
        </template>

        <AdmField
          v-if="targets.length"
          input-id="prop-target"
          label="Übernehmen in"
          hint="Beim Übernehmen des Antrags wird der Wert in dieses Feld des Mitglieds geschrieben."
        >
          <select id="prop-target" class="adm-input" :value="element.target ?? ''" @change="patch({ target: value($event) || null })">
            <option v-if="element.type !== 'photo'" value="">Nur im Antrag speichern</option>
            <option v-for="field in targets" :key="field.key" :value="field.key">
              {{ field.label }}{{ field.sensitive ? ' (Gesundheitsdaten)' : '' }}
            </option>
          </select>
        </AdmField>

        <section v-if="hasOptions" class="props__group">
          <h4>Optionen</h4>
          <div v-for="(option, index) in element.options ?? []" :key="index" class="props__option">
            <input
              class="adm-input"
              :aria-label="`Option ${index + 1} Beschriftung`"
              :value="option.label"
              @input="setOption(index, { label: value($event), value: option.value || slug(value($event)) })"
            />
            <AdmButton variant="danger" icon="pi pi-times" :aria-label="`Option ${index + 1} entfernen`" @click="removeOption(index)" />
          </div>
          <AdmButton icon="pi pi-plus" @click="addOption">Option</AdmButton>
        </section>

        <AdmField v-if="element.type === 'legal_ack'" input-id="prop-legal" label="Rechtstext">
          <select id="prop-legal" class="adm-input" :value="element.legal_kind ?? ''" @change="patch({ legal_kind: value($event) })">
            <option v-for="kind in references?.legal_kinds ?? []" :key="kind.value" :value="kind.value">{{ kind.label }}</option>
          </select>
        </AdmField>

        <template v-if="element.type === 'consent'">
          <AdmField input-id="prop-consent" label="Einwilligungsart" hint="Arten und Wortlaut werden unter Einstellungen › Datenschutz gepflegt.">
            <select id="prop-consent" class="adm-input" :value="element.consent_kind ?? ''" @change="setConsentKind(value($event))">
              <option value="" disabled>Bitte wählen</option>
              <option v-for="kind in references?.consent_kinds ?? []" :key="kind.slug" :value="kind.slug">{{ kind.label }}</option>
            </select>
          </AdmField>
          <p v-if="consentText" class="props__quote">{{ consentText }}</p>
          <AdmField input-id="prop-person" label="Erklärt von">
            <select id="prop-person" class="adm-input" :value="element.person ?? 'applicant'" @change="patch({ person: value($event) as ConsentPerson })">
              <option value="applicant">Antragsteller*in</option>
              <option value="guardians">Sorgeberechtigte</option>
            </select>
          </AdmField>
        </template>

        <AdmField v-if="element.type === 'signature'" input-id="prop-role" label="Unterschreibt">
          <select id="prop-role" class="adm-input" :value="element.role ?? 'applicant'" @change="patch({ role: value($event) as SignatureRole })">
            <option v-for="(label, role) in SIGNATURE_ROLE_LABELS" :key="role" :value="role">{{ label }}</option>
          </select>
        </AdmField>

        <section v-if="element.type === 'guardians'" class="props__group">
          <h4>Sorgeberechtigte</h4>
          <div class="props__row">
            <AdmField input-id="prop-min" label="Mindestens">
              <input id="prop-min" type="number" min="0" max="4" class="adm-input" :value="element.min ?? 1" @input="patch({ min: number($event) })" />
            </AdmField>
            <AdmField input-id="prop-max" label="Höchstens">
              <input id="prop-max" type="number" min="1" max="4" class="adm-input" :value="element.max ?? 2" @input="patch({ max: number($event) })" />
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

        <section v-if="!isContentType" class="props__group">
          <h4>Sichtbarkeit</h4>
          <AdmField input-id="prop-visibility" label="Anzeigen">
            <select id="prop-visibility" class="adm-input" :value="visibilityMode" @change="setVisibilityMode(value($event))">
              <option value="always">Immer</option>
              <option value="age">Nur unter einem Alter</option>
              <option value="field" :disabled="!earlierKeys.length">Wenn ein vorheriges Feld einen Wert hat</option>
            </select>
          </AdmField>
          <AdmField v-if="visibilityMode === 'age'" input-id="prop-age" label="Jünger als (Jahre)">
            <input id="prop-age" type="number" min="1" max="120" class="adm-input" :value="ageBelow" @input="patch({ visible_if: { age_below: number($event) } })" />
          </AdmField>
          <div v-if="visibilityMode === 'field'" class="props__row">
            <AdmField input-id="prop-vfield" label="Feld">
              <select id="prop-vfield" class="adm-input" :value="ruleField" @change="patch({ visible_if: { field: value($event), equals: ruleEquals } })">
                <option v-for="key in earlierKeys" :key="key" :value="key">{{ key }}</option>
              </select>
            </AdmField>
            <AdmField input-id="prop-vvalue" label="Wert" hint="Bei Ankreuzfeldern: ja">
              <input id="prop-vvalue" class="adm-input" :value="String(ruleEquals)" @input="setRuleValue(value($event))" />
            </AdmField>
          </div>
        </section>
      </fieldset>
    </template>

    <template v-else-if="container">
      <header class="props__head">
        <h3>{{ container.kind === 'page' ? 'Seite' : 'Abschnitt' }}</h3>
        <AdmButton variant="danger" icon="pi pi-trash" :aria-label="`${container.kind === 'page' ? 'Seite' : 'Abschnitt'} entfernen`" :disabled="readonly" @click="emit('remove-container')" />
      </header>
      <AdmField input-id="prop-container-title" label="Titel">
        <input id="prop-container-title" class="adm-input" :value="container.title" :disabled="readonly" @input="emit('rename', value($event))" />
      </AdmField>
      <div v-if="container.kind === 'page'" class="props__row">
        <AdmButton icon="pi pi-arrow-left" :disabled="readonly" @click="emit('move-page', -1)">Nach vorn</AdmButton>
        <AdmButton icon="pi pi-arrow-right" :disabled="readonly" @click="emit('move-page', 1)">Nach hinten</AdmButton>
      </div>
    </template>

    <p v-else class="props__empty">Element, Abschnitt oder Seite auswählen, um es zu bearbeiten.</p>
  </aside>
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
import { ELEMENT_LABELS, SIGNATURE_ROLE_LABELS, isContent } from '@/utils/admissionSchema'
import '../atoms/admInput.css'

interface Props {
  element: FormElement | null
  container: { kind: 'page' | 'section'; title: string } | null
  references: BuilderReferences | null
  textBlocks: AdmissionTextBlock[]
  /** answer keys of elements placed before the selected one */
  earlierKeys: string[]
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), { readonly: false })
const emit = defineEmits<{
  (e: 'update', patch: Partial<FormElement>): void
  (e: 'remove'): void
  (e: 'duplicate'): void
  (e: 'rename', title: string): void
  (e: 'remove-container'): void
  (e: 'move-page', step: -1 | 1): void
}>()

const isContentType = computed(() => !!props.element && isContent(props.element.type))
const hasKey = computed(() => !!props.element && !isContentType.value)
const hasLabel = computed(() => !!props.element && props.element.type !== 'richtext' && props.element.type !== 'divider')
const hasHelp = computed(() => !!props.element && !['signature', 'guardians', 'legal_ack', 'consent'].includes(props.element.type))
const hasOptions = computed(
  () => !!props.element && ['select', 'radio'].includes(props.element.type) && props.element.target !== 'member.gender'
)
const targets = computed(() => {
  const element = props.element
  if (!element || !props.references) return []
  return props.references.fields.member.filter(
    (field) => field.input_type === element.type || (field.input_type === 'text' && element.type === 'textarea')
  )
})
const consentText = computed(
  () => props.references?.consent_kinds.find((kind) => kind.slug === props.element?.consent_kind)?.description ?? ''
)

const visibilityMode = computed(() => {
  const rule = props.element?.visible_if
  if (!rule) return 'always'
  return 'age_below' in rule ? 'age' : 'field'
})
const ageBelow = computed(() => {
  const rule = props.element?.visible_if
  return rule && 'age_below' in rule ? rule.age_below : 18
})
const ruleField = computed(() => {
  const rule = props.element?.visible_if
  return rule && 'field' in rule ? rule.field : ''
})
const ruleEquals = computed(() => {
  const rule = props.element?.visible_if
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

function setTextBlock(raw: string) {
  patch({ text_block: raw ? Number(raw) : null })
}

function setConsentKind(slugValue: string) {
  const kind = props.references?.consent_kinds.find((entry) => entry.slug === slugValue)
  const label = props.element?.label && props.element.label !== ELEMENT_LABELS.consent ? props.element.label : kind?.label
  patch({ consent_kind: slugValue, label })
}

function setOption(index: number, option: { value: string; label: string }) {
  const options = [...(props.element?.options ?? [])]
  options[index] = option
  patch({ options })
}

function addOption() {
  const options = props.element?.options ?? []
  patch({ options: [...options, { value: `option_${options.length + 1}`, label: `Option ${options.length + 1}` }] })
}

function removeOption(index: number) {
  patch({ options: (props.element?.options ?? []).filter((_, position) => position !== index) })
}

function isNameField(target: string) {
  return target === 'guardian.name' || target === 'guardian.lastname'
}

function guardianField(target: string): GuardianFieldConfig | undefined {
  return props.element?.fields?.find((field) => field.target === target)
}

function toggleGuardianField(target: string, on: boolean) {
  const fields = props.element?.fields ?? []
  patch({ fields: on ? [...fields, { target, required: false }] : fields.filter((field) => field.target !== target) })
}

function setGuardianRequired(target: string, required: boolean) {
  patch({ fields: (props.element?.fields ?? []).map((field) => (field.target === target ? { ...field, required } : field)) })
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
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.props__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.props__head h3 {
  margin: 0;
  font-size: var(--jf-text-md);
}

.props__body {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  border: 0;
  margin: 0;
  padding: 0;
}

.props__group {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  padding-top: var(--jf-space-1);
  border-top: 1px solid var(--jf-color-border);
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
}

.props__quote {
  margin: 0;
  padding: var(--jf-space-1);
  border-left: 3px solid var(--jf-color-border);
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

.props__empty {
  color: var(--jf-color-text-muted);
}

.prop-code {
  font-family: var(--jf-font-mono);
  font-size: var(--jf-text-sm);
}
</style>
