<template>
  <div class="rule-row" :class="{ 'rule-row--invalid': rowErrors.length }" role="group" :aria-label="`Bedingung ${index + 1}`">
    <div class="rule-row__fields">
      <div class="rule-row__field">
        <label :for="`${uid}-kind`" class="sr-only">Art</label>
        <select :id="`${uid}-kind`" class="rule-row__select" :value="condition.kind" @change="onKind">
          <option v-for="kind in KIND_OPTIONS" :key="kind.value" :value="kind.value">{{ kind.label }}</option>
        </select>
      </div>
      <div class="rule-row__field">
        <label :for="`${uid}-op`" class="sr-only">Operator</label>
        <select :id="`${uid}-op`" class="rule-row__select" :value="condition.op" @change="onOp">
          <option v-for="op in OP_OPTIONS[condition.kind]" :key="op.value" :value="op.value">{{ op.label }}</option>
        </select>
      </div>
      <template v-if="condition.kind === 'age'">
        <div v-if="condition.op !== 'max'" class="rule-row__field rule-row__field--age">
          <label :for="`${uid}-min`" class="rule-row__age-label">{{ condition.op === 'between' ? 'von' : 'Jahre' }}</label>
          <input :id="`${uid}-min`" class="rule-row__number" type="number" min="0" max="120" inputmode="numeric" :value="condition.min ?? ''" @input="onAge('min', $event)">
        </div>
        <div v-if="condition.op !== 'min'" class="rule-row__field rule-row__field--age">
          <label :for="`${uid}-max`" class="rule-row__age-label">{{ condition.op === 'between' ? 'bis' : 'Jahre' }}</label>
          <input :id="`${uid}-max`" class="rule-row__number" type="number" min="0" max="120" inputmode="numeric" :value="condition.max ?? ''" @input="onAge('max', $event)">
        </div>
        <span v-if="condition.op === 'between'" class="rule-row__unit">Jahre</span>
      </template>
      <div v-else class="rule-row__field rule-row__field--values">
        <label :for="`${uid}-values`" class="sr-only">Werte</label>
        <MultiSelect
          :input-id="`${uid}-values`"
          class="rule-row__values"
          :model-value="condition.values"
          :options="options"
          option-label="label"
          option-value="value"
          :filter="condition.kind !== 'gender'"
          display="chip"
          :loading="loading"
          :placeholder="VALUE_PLACEHOLDER[condition.kind]"
          filter-placeholder="Suchen"
          empty-message="Keine Einträge"
          empty-filter-message="Keine Treffer"
          :invalid="Boolean(fieldError('values'))"
          @update:model-value="onValues"
        />
      </div>
      <Button
        icon="pi pi-times"
        severity="secondary"
        text
        class="rule-row__remove"
        aria-label="Bedingung entfernen"
        @click="emit('remove')"
      />
    </div>
    <ul v-if="rowErrors.length" class="rule-row__errors" role="alert">
      <li v-for="item in rowErrors" :key="item.field"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ item.message }}</li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import MultiSelect from 'primevue/multiselect'
import type { RuleCondition, RuleKind } from '@/api/participation'
import type { RuleOption } from '@/composables/useRuleOptions'
import { changeKind, changeOp, errorsFor, KIND_OPTIONS, OP_OPTIONS, VALUE_PLACEHOLDER } from './ruleLabels'

const props = defineProps<{
  condition: RuleCondition
  /** Server path of this row, e.g. `rules[2]` or `rules[1].rules[0]`. */
  path: string
  index: number
  options: RuleOption[]
  errors?: Record<string, string>
  loading?: boolean
  uid: string
}>()
const emit = defineEmits<{ 'update:condition': [value: RuleCondition], remove: [] }>()

const rowErrors = computed(() => errorsFor(props.errors ?? {}, props.path))
const fieldError = (field: string) => rowErrors.value.find(item => item.field === field)

function onKind(event: Event) {
  emit('update:condition', changeKind((event.target as HTMLSelectElement).value as RuleKind))
}
function onOp(event: Event) {
  emit('update:condition', changeOp(props.condition, (event.target as HTMLSelectElement).value))
}
function onValues(values: Array<number | string>) {
  if (props.condition.kind !== 'age') emit('update:condition', { ...props.condition, values })
}
function onAge(key: 'min' | 'max', event: Event) {
  const raw = (event.target as HTMLInputElement).value
  const next = { ...props.condition } as RuleCondition & { min?: number, max?: number }
  if (raw === '') delete next[key]
  else next[key] = Number(raw)
  emit('update:condition', next)
}
</script>

<style scoped>
.rule-row { display: grid; gap: var(--jf-space-1); padding: var(--jf-space-1); border-radius: var(--jf-radius-md); background: var(--jf-color-ground); border: 1px solid transparent; }
.rule-row--invalid { border-color: var(--p-red-600); }
.rule-row__fields { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1); }
.rule-row__field { display: flex; align-items: center; gap: var(--jf-space-1); }
.rule-row__field--values { flex: 1 1 14rem; min-width: 0; }
.rule-row__values { width: 100%; min-height: var(--jf-touch-target); }
.rule-row__select, .rule-row__number { min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-sm); background: var(--jf-color-card); color: var(--jf-color-text); font: inherit; }
.rule-row__number { width: 5.5rem; }
.rule-row__age-label, .rule-row__unit { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.rule-row__remove { min-width: var(--jf-touch-target); min-height: var(--jf-touch-target); }
.rule-row__errors { margin: 0; padding: 0; list-style: none; display: grid; gap: var(--jf-space-0-5); color: var(--p-red-600); font-size: var(--jf-text-sm); }
.rule-row__errors i { margin-right: var(--jf-space-0-5); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.app-dark .rule-row--invalid { border-color: var(--p-red-400); }
.app-dark .rule-row__errors { color: var(--p-red-300); }
</style>
