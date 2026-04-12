<template>
  <div class="field-checkbox">
    <Checkbox
      :id="fieldId"
      v-model="internalValue"
      :binary="true"
      :disabled="disabled"
      @change="handleChange"
    />
    <label :for="fieldId" class="ml-2">
      {{ label }}
    </label>
    <div v-if="helpText" class="ml-4">
      <small class="text-color-secondary">{{ helpText }}</small>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Checkbox from 'primevue/checkbox'

interface Props {
  modelValue: boolean
  label: string
  fieldId: string
  helpText?: string
  disabled?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'change', value: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const internalValue = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value)
})

function handleChange() {
  emit('change', internalValue.value)
}
</script>
