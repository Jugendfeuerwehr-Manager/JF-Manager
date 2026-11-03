<template>
  <div class="adm-field" :class="{ 'adm-field--inline': inline }">
    <label v-if="label" :for="inputId" class="adm-field__label">
      {{ label }}<span v-if="required" class="adm-field__required" aria-hidden="true"> *</span>
    </label>
    <slot :describedby="describedby" />
    <p v-if="hint" :id="`${inputId}-hint`" class="adm-field__hint">{{ hint }}</p>
    <p v-if="error" :id="`${inputId}-error`" class="adm-field__error" role="alert">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  inputId: string
  label?: string
  hint?: string
  error?: string
  required?: boolean
  inline?: boolean
}

const props = withDefaults(defineProps<Props>(), { label: '', hint: '', error: '', required: false, inline: false })

const describedby = computed(
  () => [props.hint && `${props.inputId}-hint`, props.error && `${props.inputId}-error`].filter(Boolean).join(' ') || undefined
)
</script>

<style scoped>
.adm-field {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
}

.adm-field--inline {
  flex-direction: row;
  align-items: center;
  gap: var(--jf-space-1);
}

.adm-field__label {
  font-weight: var(--jf-weight-semibold);
}

.adm-field__required,
.adm-field__error {
  color: var(--jf-color-danger);
}

.adm-field__hint,
.adm-field__error {
  margin: 0;
  font-size: var(--jf-text-sm);
}

.adm-field__hint {
  color: var(--jf-color-text-muted);
}
</style>
