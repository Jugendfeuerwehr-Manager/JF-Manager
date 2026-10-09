<template>
  <div class="rule-builder">
    <div class="rule-builder__sentence">
      <label :for="`${uid}-match`">Teilnehmen dürfen Personen, die</label>
      <select :id="`${uid}-match`" class="rule-builder__match" :value="modelValue.match" @change="setMatch(($event.target as HTMLSelectElement).value as RuleMatch)">
        <option value="all">alle</option>
        <option value="any">mindestens eine</option>
      </select>
      <span>der folgenden Bedingungen erfüllen:</span>
    </div>

    <p v-if="errors['']" class="rule-builder__error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors[''] }}</p>
    <p v-for="key in topLevelKeys" :key="key" class="rule-builder__error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors[key] }}</p>

    <p v-if="!modelValue.rules.length" class="rule-builder__empty">
      Keine besonderen Voraussetzungen: Alle Personen der Zielgruppe dürfen teilnehmen.
    </p>

    <div class="rule-builder__items">
      <template v-for="(item, i) in modelValue.rules" :key="i">
        <RuleRow
          v-if="!isGroup(item)"
          :uid="`${uid}-r${i}`"
          :condition="item"
          :path="`rules[${i}]`"
          :index="i"
          :options="optionsFor(item.kind)"
          :errors="errors"
          :loading="loading"
          @update:condition="setItem(i, $event)"
          @remove="removeItem(i)"
        />
        <fieldset v-else class="rule-group">
          <legend class="rule-group__legend">
            <label :for="`${uid}-g${i}-match`">Untergruppe: erfüllt</label>
            <select :id="`${uid}-g${i}-match`" class="rule-builder__match" :value="item.match" @change="setGroupMatch(i, ($event.target as HTMLSelectElement).value as RuleMatch)">
              <option value="all">alle</option>
              <option value="any">mindestens eine</option>
            </select>
            <span>der folgenden Bedingungen</span>
          </legend>
          <p v-for="key in groupKeys(i)" :key="key" class="rule-builder__error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors[key] }}</p>
          <RuleRow
            v-for="(cond, j) in item.rules"
            :key="j"
            :uid="`${uid}-g${i}-r${j}`"
            :condition="cond"
            :path="`rules[${i}].rules[${j}]`"
            :index="j"
            :options="optionsFor(cond.kind)"
            :errors="errors"
            :loading="loading"
            @update:condition="setGroupItem(i, j, $event)"
            @remove="removeGroupItem(i, j)"
          />
          <div class="rule-builder__actions">
            <Button label="Bedingung hinzufügen" icon="pi pi-plus" severity="secondary" outlined @click="addGroupItem(i)" />
            <Button label="Gruppe entfernen" icon="pi pi-trash" severity="secondary" text @click="removeItem(i)" />
          </div>
        </fieldset>
      </template>
    </div>

    <div class="rule-builder__actions">
      <Button label="Bedingung hinzufügen" icon="pi pi-plus" severity="secondary" outlined @click="addItem" />
      <Button label="Bedingungsgruppe hinzufügen" icon="pi pi-sitemap" severity="secondary" outlined @click="addGroup" />
    </div>

    <p v-if="summary" class="rule-builder__summary"><strong>Zusammengefasst:</strong> {{ summary }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import RuleRow from './RuleRow.vue'
import type { Rule, RuleCondition, RuleErrors, RuleGroup, RuleKind, RuleMatch } from '@/api/participation'
import type { RuleOption } from '@/composables/useRuleOptions'
import { isGroup, newCondition } from './ruleLabels'

const props = withDefaults(defineProps<{
  modelValue: Rule
  errors?: RuleErrors
  options: Record<string, RuleOption[]>
  loading?: boolean
  summary?: string | null
  uid?: string
}>(), { errors: () => ({}), loading: false, summary: null, uid: 'rule' })
const emit = defineEmits<{ 'update:modelValue': [value: Rule] }>()

const topLevelKeys = computed(() => ['match', 'rules', 'v'].filter(key => props.errors[key]))
const groupKeys = (i: number) => [`rules[${i}].match`, `rules[${i}].rules`].filter(key => props.errors[key])
const optionsFor = (kind: RuleKind) => props.options[kind] ?? []

function commit(mutate: (rule: Rule) => void) {
  const next = JSON.parse(JSON.stringify(props.modelValue)) as Rule
  mutate(next)
  emit('update:modelValue', next)
}
const groupAt = (rule: Rule, i: number) => rule.rules[i] as RuleGroup

const setMatch = (match: RuleMatch) => commit(rule => { rule.match = match })
const addItem = () => commit(rule => { rule.rules.push(newCondition()) })
const addGroup = () => commit(rule => { rule.rules.push({ match: 'any', rules: [newCondition()] }) })
const removeItem = (i: number) => commit(rule => { rule.rules.splice(i, 1) })
const setItem = (i: number, value: RuleCondition) => commit(rule => { rule.rules[i] = value })
const setGroupMatch = (i: number, match: RuleMatch) => commit(rule => { groupAt(rule, i).match = match })
const addGroupItem = (i: number) => commit(rule => { groupAt(rule, i).rules.push(newCondition()) })
const setGroupItem = (i: number, j: number, value: RuleCondition) => commit(rule => { groupAt(rule, i).rules[j] = value })
// An emptied group would be rejected by the server; remove it with its last condition.
const removeGroupItem = (i: number, j: number) => commit(rule => {
  const group = groupAt(rule, i)
  group.rules.splice(j, 1)
  if (!group.rules.length) rule.rules.splice(i, 1)
})
</script>

<style scoped>
.rule-builder { display: grid; gap: var(--jf-space-2); }
.rule-builder__sentence { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1); }
.rule-builder__match { min-height: var(--jf-touch-target); padding: 0 var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-sm); background: var(--jf-color-card); color: var(--jf-color-text); font: inherit; font-weight: var(--jf-weight-semibold); }
.rule-builder__items { display: grid; gap: var(--jf-space-1); }
.rule-builder__empty { margin: 0; color: var(--jf-color-text-muted); }
.rule-builder__actions { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); }
.rule-builder__summary { margin: 0; padding: var(--jf-space-1-5) var(--jf-space-2); border-radius: var(--jf-radius-md); background: var(--jf-color-ground); }
.rule-builder__error { margin: 0; color: var(--p-red-600); font-size: var(--jf-text-sm); }
.rule-builder__error i { margin-right: var(--jf-space-0-5); }
.rule-group { display: grid; gap: var(--jf-space-1); margin: 0 0 0 var(--jf-space-3); padding: var(--jf-space-1) var(--jf-space-2) var(--jf-space-2); border: 1px solid var(--jf-color-border); border-left-width: 4px; border-radius: var(--jf-radius-md); }
.rule-group__legend { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1); padding: 0 var(--jf-space-1); }
.app-dark .rule-builder__error { color: var(--p-red-300); }
</style>
