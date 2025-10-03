<template>
  <div class="search-input-wrapper">
    <IconField iconPosition="left">
      <InputIcon>
        <i class="pi pi-search"></i>
      </InputIcon>
      <InputText
        :model-value="modelValue"
        @input="onInput"
        :placeholder="placeholder"
        :disabled="disabled"
        class="w-full"
      />
    </IconField>
    <small v-if="hint" class="search-hint">{{ hint }}</small>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import InputText from 'primevue/inputtext';
import IconField from 'primevue/iconfield';
import InputIcon from 'primevue/inputicon';

interface Props {
  modelValue: string;
  placeholder?: string;
  debounceDelay?: number;
  disabled?: boolean;
  hint?: string;
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'Suchen...',
  debounceDelay: 300,
  disabled: false,
  hint: ''
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
  (e: 'search', value: string): void;
}>();

let debounceTimeout: ReturnType<typeof setTimeout> | null = null;

const onInput = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const value = target.value;
  
  // Immediately update v-model
  emit('update:modelValue', value);
  
  // Debounced search event
  if (debounceTimeout) {
    clearTimeout(debounceTimeout);
  }
  
  debounceTimeout = setTimeout(() => {
    emit('search', value);
  }, props.debounceDelay);
};
</script>

<style scoped>
.search-input-wrapper {
  width: 100%;
}

.search-hint {
  display: block;
  margin-top: 0.25rem;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

:deep(.p-inputtext) {
  border-radius: 8px;
  transition: all 0.3s ease;
}

:deep(.p-inputtext:hover) {
  border-color: var(--primary-color);
}

:deep(.p-inputtext:focus) {
  box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
}
</style>
