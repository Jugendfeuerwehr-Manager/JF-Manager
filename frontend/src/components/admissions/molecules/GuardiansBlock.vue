<template>
  <fieldset class="guardians">
    <legend class="guardians__legend">{{ element.label || 'Sorgeberechtigte' }}</legend>
    <section v-for="(guardian, index) in rows" :key="index" class="guardians__person" :aria-label="`${index + 1}. Person`">
      <header class="guardians__head">
        <h4>{{ index + 1 }}. Erziehungsberechtigte*r</h4>
        <AdmButton
          v-if="index >= minimum"
          variant="danger"
          icon="pi pi-trash"
          :disabled="disabled"
          :aria-label="`${index + 1}. Person entfernen`"
          @click="remove(index)"
        />
      </header>
      <div class="guardians__grid">
        <AdmField
          v-for="field in element.fields ?? []"
          :key="field.target"
          :input-id="`${element.id}-${index}-${field.target}`"
          :label="meta(field.target).label"
          :required="field.required"
        >
          <input
            :id="`${element.id}-${index}-${field.target}`"
            class="adm-input"
            :type="meta(field.target).input"
            :value="guardian[guardianField(field.target)] ?? ''"
            :disabled="disabled"
            @input="update(index, field.target, ($event.target as HTMLInputElement).value)"
          />
        </AdmField>
      </div>
    </section>
    <AdmButton v-if="rows.length < maximum" icon="pi pi-plus" :disabled="disabled" @click="add">
      Weitere*n Erziehungsberechtigte*n hinzufügen
    </AdmButton>
    <p v-if="error" class="guardians__error" role="alert">{{ error }}</p>
  </fieldset>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AdmButton from '../atoms/AdmButton.vue'
import AdmField from '../atoms/AdmField.vue'
import type { FormElement } from '@/types/admissions'
import { GUARDIAN_FIELD_META, guardianField } from '@/utils/admissionSchema'
import '../atoms/admInput.css'

type Guardian = Record<string, string>

interface Props {
  element: FormElement
  modelValue: Guardian[]
  disabled?: boolean
  error?: string
}

const props = withDefaults(defineProps<Props>(), { disabled: false, error: '' })
const emit = defineEmits<{ (e: 'update:modelValue', value: Guardian[]): void }>()

const minimum = computed(() => Math.max(props.element.min ?? 1, 1))
const maximum = computed(() => props.element.max ?? 2)
// Always show at least the required number of people.
const rows = computed(() => {
  const missing = Math.max(minimum.value - props.modelValue.length, 0)
  return [...props.modelValue, ...Array.from({ length: missing }, () => ({}) as Guardian)]
})

function meta(target: string) {
  return GUARDIAN_FIELD_META[target] ?? { label: target, input: 'text' as const }
}

function update(index: number, target: string, value: string) {
  const next = rows.value.map((row) => ({ ...row }))
  next[index] = { ...next[index], [guardianField(target)]: value }
  emit('update:modelValue', next)
}

function add() {
  emit('update:modelValue', [...rows.value, {}])
}

function remove(index: number) {
  emit('update:modelValue', rows.value.filter((_, position) => position !== index))
}
</script>

<style scoped>
.guardians {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  border: 0;
  margin: 0;
  padding: 0;
}

.guardians__legend {
  font-weight: var(--jf-weight-semibold);
}

.guardians__person {
  padding: var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
}

.guardians__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.guardians__head h4 {
  margin: 0;
  font-size: var(--jf-text-md);
}

.guardians__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: var(--jf-space-1-5);
  margin-top: var(--jf-space-1);
}

.guardians__error {
  margin: 0;
  color: #b91c1c;
  font-size: var(--jf-text-sm);
}
</style>
