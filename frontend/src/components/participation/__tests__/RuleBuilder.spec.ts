import PrimeVue from 'primevue/config'
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import RuleBuilder from '../RuleBuilder.vue'
import type { Rule } from '@/api/participation'

const options = {
  qualification: [{ value: 1, label: 'Truppmann' }, { value: 2, label: 'Maschinist' }],
  special_task: [], gender: [{ value: 'female', label: 'weiblich' }], group: [], status: [], department: [],
}
const empty = (): Rule => ({ v: 1, match: 'all', rules: [] })

function mountBuilder(modelValue: Rule, errors: Record<string, string> = {}) {
  return mount(RuleBuilder, { props: { modelValue, options, errors }, global: { plugins: [PrimeVue] } })
}
const last = (wrapper: ReturnType<typeof mountBuilder>) => (wrapper.emitted('update:modelValue')!.at(-1)![0]) as Rule
const button = (wrapper: ReturnType<typeof mountBuilder>, label: string) => wrapper.findAll('button').find(b => b.text().includes(label))!

describe('RuleBuilder', () => {
  it('shows the sentence and the empty-rule hint', () => {
    const wrapper = mountBuilder(empty())
    expect(wrapper.text()).toContain('Teilnehmen dürfen Personen, die')
    expect(wrapper.text()).toContain('Keine besonderen Voraussetzungen')
  })

  it('adds a condition as valid rule JSON and switches the combination', async () => {
    const wrapper = mountBuilder(empty())
    await button(wrapper, 'Bedingung hinzufügen').trigger('click')
    expect(last(wrapper)).toEqual({ v: 1, match: 'all', rules: [{ kind: 'qualification', op: 'has_any', values: [] }] })
    await wrapper.find('select').setValue('any')
    expect(last(wrapper).match).toBe('any')
  })

  it('changes the kind of a row and resets operator and values', async () => {
    const rule: Rule = { v: 1, match: 'all', rules: [{ kind: 'qualification', op: 'has_all', values: [1] }] }
    const wrapper = mountBuilder(rule)
    await wrapper.find('select[id$="-kind"]').setValue('age')
    expect(last(wrapper).rules[0]).toEqual({ kind: 'age', op: 'min', min: 18 })
  })

  it('edits age bounds as numbers and offers min/max for "between"', async () => {
    const rule: Rule = { v: 1, match: 'all', rules: [{ kind: 'age', op: 'between', min: 10, max: 17 }] }
    const wrapper = mountBuilder(rule)
    const inputs = wrapper.findAll('input[type="number"]')
    expect(inputs).toHaveLength(2)
    await inputs[1]!.setValue('16')
    expect(last(wrapper).rules[0]).toEqual({ kind: 'age', op: 'between', min: 10, max: 16 })
  })

  it('removes a row', async () => {
    const rule: Rule = { v: 1, match: 'all', rules: [{ kind: 'age', op: 'min', min: 18 }, { kind: 'age', op: 'max', max: 30 }] }
    const wrapper = mountBuilder(rule)
    await wrapper.findAll('button[aria-label="Bedingung entfernen"]')[0]!.trigger('click')
    expect(last(wrapper).rules).toEqual([{ kind: 'age', op: 'max', max: 30 }])
  })

  it('adds one nested group with its own match and conditions, and drops it with its last condition', async () => {
    const wrapper = mountBuilder(empty())
    await button(wrapper, 'Bedingungsgruppe hinzufügen').trigger('click')
    expect(last(wrapper).rules).toEqual([{ match: 'any', rules: [{ kind: 'qualification', op: 'has_any', values: [] }] }])

    const grouped: Rule = last(wrapper)
    const group = mountBuilder(grouped)
    expect(group.find('fieldset').exists()).toBe(true)
    // inside a group there is no further "group" button
    expect(group.findAll('fieldset button').some(b => b.text().includes('Bedingungsgruppe'))).toBe(false)
    await group.find('fieldset select').setValue('all')
    expect((last(group).rules[0] as { match: string }).match).toBe('all')
    await group.find('fieldset button[aria-label="Bedingung entfernen"]').trigger('click')
    expect(last(group).rules).toEqual([])
  })

  it('shows server errors at the row they belong to', () => {
    const rule: Rule = { v: 1, match: 'all', rules: [
      { kind: 'age', op: 'min', min: 18 },
      { kind: 'age', op: 'between', min: 20, max: 10 },
    ] }
    const wrapper = mountBuilder(rule, { 'rules[1].max': 'Mindestalter größer als Höchstalter' })
    const rows = wrapper.findAll('.rule-row')
    expect(rows[0]!.text()).not.toContain('Mindestalter größer')
    expect(rows[1]!.text()).toContain('Mindestalter größer als Höchstalter')
    expect(rows[1]!.attributes('role')).toBe('group')
  })

  it('shows errors of nested rows and groups', () => {
    const rule: Rule = { v: 1, match: 'all', rules: [{ match: 'any', rules: [{ kind: 'age', op: 'min', min: 200 }] }] }
    const wrapper = mountBuilder(rule, { 'rules[0].rules[0].min': 'Alter muss eine ganze Zahl von 0 bis 120 sein' })
    expect(wrapper.find('fieldset').text()).toContain('Alter muss eine ganze Zahl')
  })

  it('renders the server summary', () => {
    const wrapper = mount(RuleBuilder, { props: { modelValue: empty(), options, summary: 'Maschinist und Alter ab 18' }, global: { plugins: [PrimeVue] } })
    expect(wrapper.text()).toContain('Zusammengefasst: Maschinist und Alter ab 18')
  })
})
