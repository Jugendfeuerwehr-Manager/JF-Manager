<template>
  <h3 v-if="element.type === 'heading'" class="el-heading">{{ element.label }}</h3>
  <!-- html is sanitised by the backend (text blocks and published versions); the builder preview shows drafts -->
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div v-else-if="element.type === 'richtext'" class="el-richtext" v-html="element.html"></div>
  <hr v-else-if="element.type === 'divider'" class="el-divider" />

  <AdmField
    v-else-if="isTextual"
    :input-id="inputId"
    :label="element.label"
    :hint="element.help"
    :error="error"
    :required="element.required"
  >
    <template #default="{ describedby }">
      <textarea
        v-if="element.type === 'textarea'"
        :id="inputId"
        class="adm-input"
        :value="stringValue"
        :disabled="disabled"
        :aria-describedby="describedby"
        :aria-invalid="!!error"
        @input="emitValue(($event.target as HTMLTextAreaElement).value)"
      ></textarea>
      <input
        v-else
        :id="inputId"
        class="adm-input"
        :type="nativeType"
        :value="stringValue"
        :disabled="disabled"
        :autocomplete="autocomplete"
        :aria-describedby="describedby"
        :aria-invalid="!!error"
        @input="emitValue(($event.target as HTMLInputElement).value)"
      />
    </template>
  </AdmField>

  <AdmField
    v-else-if="element.type === 'select'"
    :input-id="inputId"
    :label="element.label"
    :hint="element.help"
    :error="error"
    :required="element.required"
  >
    <template #default="{ describedby }">
      <select
        :id="inputId"
        class="adm-input"
        :value="stringValue"
        :disabled="disabled"
        :aria-describedby="describedby"
        :aria-invalid="!!error"
        @change="emitValue(($event.target as HTMLSelectElement).value)"
      >
        <option value="">Bitte wählen</option>
        <option v-for="option in options" :key="option.value" :value="option.value">{{ option.label }}</option>
      </select>
    </template>
  </AdmField>

  <fieldset v-else-if="element.type === 'radio'" class="el-group" :aria-describedby="error ? `${inputId}-error` : undefined">
    <legend class="el-legend">{{ element.label }}<span v-if="element.required" class="el-required"> *</span></legend>
    <label v-for="option in options" :key="option.value" class="el-choice">
      <input
        type="radio"
        class="adm-check"
        :name="inputId"
        :value="option.value"
        :checked="modelValue === option.value"
        :disabled="disabled"
        @change="emitValue(option.value)"
      />
      <span>{{ option.label }}</span>
    </label>
    <p v-if="element.help" class="el-hint">{{ element.help }}</p>
    <p v-if="error" :id="`${inputId}-error`" class="el-error" role="alert">{{ error }}</p>
  </fieldset>

  <div v-else-if="element.type === 'checkbox'" class="el-group">
    <label class="el-choice">
      <input
        :id="inputId"
        type="checkbox"
        class="adm-check"
        :checked="modelValue === true"
        :disabled="disabled"
        @change="emitValue(($event.target as HTMLInputElement).checked)"
      />
      <span>{{ element.label }}<span v-if="element.required" class="el-required"> *</span></span>
    </label>
    <p v-if="element.help" class="el-hint">{{ element.help }}</p>
    <p v-if="error" class="el-error" role="alert">{{ error }}</p>
  </div>

  <div v-else-if="element.type === 'legal_ack' || element.type === 'consent'" class="el-group el-legal">
    <details v-if="legalText" class="el-legal__text">
      <summary>{{ legalTitle }}</summary>
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div v-html="legalText"></div>
    </details>
    <p v-else class="el-hint">{{ legalPlaceholder }}</p>
    <label class="el-choice">
      <input
        :id="inputId"
        type="checkbox"
        class="adm-check"
        :checked="modelValue === true"
        :disabled="disabled"
        @change="emitValue(($event.target as HTMLInputElement).checked)"
      />
      <span>
        {{ element.label }}<span v-if="element.required" class="el-required"> *</span>
        <span v-if="element.type === 'consent' && element.person === 'guardians'" class="el-hint">
          (Erklärung der Sorgeberechtigten)</span
        >
      </span>
    </label>
    <p v-if="error" class="el-error" role="alert">{{ error }}</p>
  </div>

  <AdmField
    v-else-if="element.type === 'photo'"
    :input-id="inputId"
    :label="element.label"
    :hint="element.help || 'JPG oder PNG, z. B. ein Handyfoto vor hellem Hintergrund.'"
    :error="error"
    :required="element.required"
  >
    <template #default="{ describedby }">
      <input
        :id="inputId"
        type="file"
        accept="image/jpeg,image/png"
        class="adm-input"
        :disabled="disabled"
        :aria-describedby="describedby"
        @change="onPhoto"
      />
      <img v-if="photoSrc" :src="photoSrc" alt="Vorschau des Passbilds" class="el-photo" />
    </template>
  </AdmField>

  <fieldset v-else-if="element.type === 'signature'" class="el-group">
    <legend class="el-legend">
      {{ element.label || SIGNATURE_ROLE_LABELS[element.role ?? 'applicant'] }}<span v-if="element.required" class="el-required">
        *</span
      >
    </legend>
    <SignaturePad
      :model-value="stringValue"
      :label="`Unterschrift ${SIGNATURE_ROLE_LABELS[element.role ?? 'applicant']}`"
      :disabled="disabled"
      @update:model-value="emitValue"
    />
    <p v-if="error" class="el-error" role="alert">{{ error }}</p>
  </fieldset>

  <GuardiansBlock
    v-else-if="element.type === 'guardians'"
    :element="element"
    :model-value="guardians"
    :disabled="disabled"
    :error="error"
    @update:model-value="emitValue"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import AdmField from '../atoms/AdmField.vue'
import SignaturePad from '../atoms/SignaturePad.vue'
import GuardiansBlock from './GuardiansBlock.vue'
import type { FormElement } from '@/types/admissions'
import { GENDER_OPTIONS, SIGNATURE_ROLE_LABELS } from '@/utils/admissionSchema'
import '../atoms/admInput.css'

interface Props {
  element: FormElement
  modelValue?: unknown
  error?: string
  disabled?: boolean
  idPrefix?: string
}

const props = withDefaults(defineProps<Props>(), { modelValue: undefined, error: '', disabled: false, idPrefix: 'adm' })
const emit = defineEmits<{ (e: 'update:modelValue', value: unknown): void }>()

const inputId = computed(() => `${props.idPrefix}-${props.element.id}`)
const isTextual = computed(() => ['text', 'textarea', 'date', 'email', 'phone'].includes(props.element.type))
const nativeType = computed(() => ({ phone: 'tel', email: 'email', date: 'date' })[props.element.type as string] ?? 'text')
const stringValue = computed(() => (typeof props.modelValue === 'string' ? props.modelValue : ''))
const guardians = computed(() => (Array.isArray(props.modelValue) ? (props.modelValue as Record<string, string>[]) : []))
const options = computed(() => (props.element.target === 'member.gender' ? GENDER_OPTIONS : (props.element.options ?? [])))
const photoPreview = ref('')
const photoSrc = computed(() => photoPreview.value || (stringValue.value.startsWith('data:image/') ? stringValue.value : ''))

const AUTOCOMPLETE: Record<string, string> = {
  'member.name': 'given-name',
  'member.lastname': 'family-name',
  'member.birthday': 'bday',
  'member.street': 'street-address',
  'member.zip_code': 'postal-code',
  'member.city': 'address-level2',
  'member.email': 'email',
  'member.mobile': 'tel',
  'member.phone': 'tel'
}
const autocomplete = computed(() => AUTOCOMPLETE[props.element.target ?? ''] ?? 'off')

const legalTitle = computed(() => props.element.legal?.title ?? props.element.consent?.label ?? '')
const legalText = computed(() => props.element.legal?.body ?? (props.element.consent?.text ? `<p>${escapeHtml(props.element.consent.text)}</p>` : ''))
const legalPlaceholder = computed(() =>
  props.element.type === 'legal_ack'
    ? 'Der veröffentlichte Rechtstext wird hier zum Aufklappen angezeigt.'
    : 'Der Wortlaut der Einwilligung wird hier angezeigt.'
)

function escapeHtml(text: string) {
  return text.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`)
}

function emitValue(value: unknown) {
  emit('update:modelValue', value)
}

const PHOTO_MAX_PX = 1200

// Phone photos are large; scale down before sending (the request body is limited).
async function onPhoto(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const url = URL.createObjectURL(file)
  try {
    const image = new Image()
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve()
      image.onerror = () => reject(new Error('Bild konnte nicht gelesen werden'))
      image.src = url
    })
    const scale = Math.min(1, PHOTO_MAX_PX / Math.max(image.width, image.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(image.width * scale)
    canvas.height = Math.round(image.height * scale)
    canvas.getContext('2d')?.drawImage(image, 0, 0, canvas.width, canvas.height)
    photoPreview.value = canvas.toDataURL('image/jpeg', 0.85)
    emitValue(photoPreview.value)
  } catch {
    photoPreview.value = ''
    emitValue('')
  } finally {
    URL.revokeObjectURL(url)
  }
}
</script>

<style scoped>
.el-heading {
  margin: var(--jf-space-1) 0 0;
  font-size: var(--jf-text-lg);
}

.el-richtext :deep(p) {
  margin: 0 0 var(--jf-space-1);
}

.el-divider {
  border: 0;
  border-top: 1px solid var(--jf-color-border);
  margin: var(--jf-space-1) 0;
}

.el-group {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  border: 0;
  margin: 0;
  padding: 0;
}

.el-legend {
  padding: 0;
  margin-bottom: var(--jf-space-0-5);
  font-weight: var(--jf-weight-semibold);
}

.el-choice {
  display: flex;
  align-items: flex-start;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target, 44px);
  padding-top: 0.6rem;
  cursor: pointer;
}

.el-required,
.el-error {
  color: var(--jf-color-danger);
}

.el-hint,
.el-error {
  margin: 0;
  font-size: var(--jf-text-sm);
}

.el-hint {
  color: var(--jf-color-text-muted);
}

.el-legal__text {
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
  font-size: var(--jf-text-sm);
}

.el-legal__text summary {
  cursor: pointer;
  font-weight: var(--jf-weight-semibold);
}

.el-photo {
  max-width: 140px;
  border-radius: var(--jf-radius-sm);
}
</style>
