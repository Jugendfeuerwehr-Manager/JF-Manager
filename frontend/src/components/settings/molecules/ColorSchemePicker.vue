<template>
  <fieldset class="scheme-picker" :disabled="disabled">
    <legend class="scheme-picker__legend">Farbschema</legend>
    <p class="scheme-picker__help">
      Grundfarbe für Schaltflächen, Links und Hervorhebungen. Abstufungen für hellen und dunklen Modus werden
      automatisch kontraststark abgeleitet; Status- und Warnfarben bleiben unverändert.
    </p>

    <div class="scheme-picker__options" role="radiogroup" aria-label="Farbschema wählen">
      <button
        v-for="scheme in COLOR_SCHEMES"
        :key="scheme.key"
        type="button"
        role="radio"
        class="scheme-option"
        :class="{ 'scheme-option--active': selectedKey === scheme.key }"
        :aria-checked="selectedKey === scheme.key"
        @click="emit('update:modelValue', scheme.color)"
      >
        <span class="scheme-option__swatch" :style="{ backgroundColor: scheme.color }" aria-hidden="true"></span>
        <span>{{ scheme.label }}</span>
        <i v-if="selectedKey === scheme.key" class="pi pi-check" aria-hidden="true"></i>
      </button>
      <button
        type="button"
        role="radio"
        class="scheme-option"
        :class="{ 'scheme-option--active': selectedKey === 'custom' }"
        :aria-checked="selectedKey === 'custom'"
        @click="chooseCustom"
      >
        <span class="scheme-option__swatch scheme-option__swatch--custom" aria-hidden="true"></span>
        <span>Eigene Farbe</span>
        <i v-if="selectedKey === 'custom'" class="pi pi-check" aria-hidden="true"></i>
      </button>
    </div>

    <div v-if="selectedKey === 'custom' || customOpen" class="scheme-picker__custom">
      <label for="brand-color-input">Farbwert</label>
      <div class="scheme-picker__custom-row">
        <input
          type="color"
          class="scheme-picker__native"
          :value="normalized"
          aria-label="Farbe auswählen"
          @input="onNative"
        />
        <InputText
          id="brand-color-input"
          v-model="hexInput"
          :invalid="hexInvalid"
          aria-describedby="brand-color-error"
          placeholder="#rrggbb"
          maxlength="7"
          @update:model-value="onHex"
        />
      </div>
      <small v-if="hexInvalid" id="brand-color-error" class="scheme-picker__error">Bitte eine Farbe im Format #rrggbb angeben.</small>
    </div>

    <div class="scheme-preview" aria-label="Vorschau">
      <div v-for="mode in previews" :key="mode.key" class="scheme-preview__panel" :style="mode.panel">
        <span class="scheme-preview__mode">{{ mode.label }}</span>
        <span class="scheme-preview__button" :style="mode.button">Hauptaktion</span>
        <span class="scheme-preview__link" :style="mode.link">Link öffnen</span>
        <span class="scheme-preview__nav" :style="mode.nav">Aktiver Eintrag</span>
      </div>
    </div>
    <p v-if="adjusted" class="scheme-picker__note" role="status">
      <i class="pi pi-info-circle" aria-hidden="true"></i>
      Für ausreichenden Kontrast werden Schaltflächen im hellen Modus in {{ resolved.light.color }} dargestellt.
    </p>
  </fieldset>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import InputText from 'primevue/inputtext'
import { COLOR_SCHEMES, normalizeBrandColor, resolveBrand } from '@/theme/brand'
import { roles } from '@/theme/palette'

const props = withDefaults(defineProps<{ modelValue?: string | null; disabled?: boolean }>(), {
  modelValue: null,
  disabled: false,
})
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const HEX = /^#[0-9a-fA-F]{6}$/
const normalized = computed(() => normalizeBrandColor(props.modelValue))
const selectedKey = computed(() => COLOR_SCHEMES.find(s => s.color === normalized.value)?.key ?? 'custom')
const resolved = computed(() => resolveBrand(normalized.value))
const adjusted = computed(() => resolved.value.light.color !== normalized.value)

const customOpen = ref(false)
const hexInput = ref(normalized.value)
const hexInvalid = computed(() => !HEX.test(hexInput.value.trim()))
watch(normalized, value => { if (HEX.test(hexInput.value) && normalizeBrandColor(hexInput.value) !== value) hexInput.value = value })

function chooseCustom() {
  customOpen.value = true
  hexInput.value = normalized.value
}

function onNative(event: Event) {
  const value = (event.target as HTMLInputElement).value
  hexInput.value = value
  emit('update:modelValue', value.toLowerCase())
}

function onHex(value: string | undefined) {
  const candidate = (value ?? '').trim()
  if (HEX.test(candidate)) emit('update:modelValue', candidate.toLowerCase())
}

const previews = computed(() => {
  const { light, dark, scale } = resolved.value
  return [
    {
      key: 'light',
      label: 'Hell',
      panel: { background: roles.light.ground, color: roles.light.text },
      button: { background: light.color, color: light.onColor },
      link: { color: light.color },
      nav: { background: scale[50], color: light.highlightText },
    },
    {
      key: 'dark',
      label: 'Dunkel',
      panel: { background: roles.dark.ground, color: roles.dark.text },
      button: { background: dark.color, color: dark.onColor },
      link: { color: dark.color },
      nav: { background: `color-mix(in srgb, ${dark.color}, transparent 84%)`, color: roles.dark.text },
    },
  ]
})
</script>

<style scoped>
.scheme-picker {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  margin: var(--jf-space-2) 0 0;
  padding: 0;
  border: 0;
  min-width: 0;
}

.scheme-picker__legend {
  padding: 0;
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text);
}

.scheme-picker__help,
.scheme-picker__note {
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.scheme-picker__note {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
}

.scheme-picker__options {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: var(--jf-space-1);
}

.scheme-option {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  padding: 0 var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-medium);
  text-align: left;
  cursor: pointer;
}

.scheme-option .pi-check {
  margin-left: auto;
  color: var(--jf-color-primary);
}

.scheme-option--active {
  border-color: var(--jf-color-primary);
  box-shadow: inset 0 0 0 1px var(--jf-color-primary);
  font-weight: var(--jf-weight-semibold);
}

.scheme-option:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.scheme-option__swatch {
  flex: none;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(23, 32, 51, 0.15);
}

.scheme-option__swatch--custom {
  background: conic-gradient(#b91c1c, #c2410c, #15803d, #0f766e, #1d4ed8, #7e22ce, #b91c1c);
}

.scheme-picker__custom {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  font-size: var(--jf-text-sm);
}

.scheme-picker__custom-row {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
}

.scheme-picker__native {
  width: var(--jf-touch-target);
  height: var(--jf-touch-target);
  padding: 2px;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  cursor: pointer;
}

.scheme-picker__error {
  color: var(--p-red-700);
  font-weight: var(--jf-weight-semibold);
}

.app-dark .scheme-picker__error {
  color: var(--p-red-300);
}

.scheme-preview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--jf-space-1);
}

.scheme-preview__panel {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1) var(--jf-space-1-5);
  padding: var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
}

.scheme-preview__mode {
  flex-basis: 100%;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.8;
}

.scheme-preview__button {
  padding: 6px 12px;
  border-radius: var(--jf-radius-md);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
}

.scheme-preview__link {
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  text-decoration: underline;
}

.scheme-preview__nav {
  padding: 4px 10px;
  border-radius: var(--jf-radius-sm);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
}
</style>
