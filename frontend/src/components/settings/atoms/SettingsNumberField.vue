<template>
  <div class="field">
    <label :for="fieldId" class="block mb-2">
      {{ label }}
      <span v-if="required" class="text-red-500">*</span>
    </label>
    <InputNumber
      :id="fieldId"
      v-model="internalValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :min="min"
      :max="max"
      class="w-full"
      :inputClass="'w-full'"
      @blur="handleBlur"
    />
    <small v-if="helpText" class="text-color-secondary">{{ helpText }}</small>
    <small v-if="errorMessage" class="text-red-500 block mt-1">{{ errorMessage }}</small>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import InputNumber from 'primevue/inputnumber'

interface Props {
  modelValue: number | null
  label: string
  fieldId: string
  placeholder?: string
  helpText?: string
  required?: boolean
  disabled?: boolean
  errorMessage?: string
  min?: number
  max?: number
}

interface Emits {
  (e: 'update:modelValue', value: number | null): void
  (e: 'blur'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const internalValue = computed({
  get: () => props.modelValue,
  set: (value: number | null) => emit('update:modelValue', value)
})

function handleBlur() {
  emit('blur')
}
</script>
