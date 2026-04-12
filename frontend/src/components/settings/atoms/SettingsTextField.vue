<template>
  <div class="field">
    <label :for="fieldId" class="block mb-2">
      {{ label }}
      <span v-if="required" class="text-red-500">*</span>
    </label>
    <InputText
      :id="fieldId"
      v-model="internalValue"
      :placeholder="placeholder"
      :disabled="disabled"
      class="w-full"
      @blur="handleBlur"
    />
    <small v-if="helpText" class="text-color-secondary">{{ helpText }}</small>
    <small v-if="errorMessage" class="text-red-500 block mt-1">{{ errorMessage }}</small>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import InputText from 'primevue/inputtext'

interface Props {
  modelValue: string
  label: string
  fieldId: string
  placeholder?: string
  helpText?: string
  required?: boolean
  disabled?: boolean
  errorMessage?: string
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'blur'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const internalValue = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value)
})

function handleBlur() {
  emit('blur')
}
</script>
