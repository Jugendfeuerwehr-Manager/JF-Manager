import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ColorSchemePicker from '../molecules/ColorSchemePicker.vue'
import GeneralSettingsForm from '../molecules/GeneralSettingsForm.vue'

const global = { plugins: [PrimeVue] }

describe('ColorSchemePicker', () => {
  it('marks the active scheme and selects another', async () => {
    const wrapper = mount(ColorSchemePicker, { props: { modelValue: '#b91c1c' }, global })
    const radios = wrapper.findAll('[role="radio"]')
    expect(radios.map(r => r.text())).toEqual(['Feuerwehrrot', 'Blau', 'Grün', 'Orange', 'Petrol', 'Eigene Farbe'])
    expect(radios[0]!.attributes('aria-checked')).toBe('true')
    await radios[1]!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['#1d4ed8'])
  })

  it('accepts only valid custom hex values and explains contrast adjustments', async () => {
    const wrapper = mount(ColorSchemePicker, { props: { modelValue: '#ffff00' }, global })
    expect(wrapper.find('[aria-checked="true"]').text()).toContain('Eigene Farbe')
    expect(wrapper.text()).toContain('Für ausreichenden Kontrast')
    const input = wrapper.get('#brand-color-input')
    await input.setValue('#12')
    expect(wrapper.text()).toContain('Format #rrggbb')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    await input.setValue('#0F766E')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['#0f766e'])
  })

  it('is read-only without change permission', () => {
    const wrapper = mount(ColorSchemePicker, { props: { modelValue: '#b91c1c', disabled: true }, global })
    expect(wrapper.get('fieldset').attributes('disabled')).toBeDefined()
  })
})

describe('GeneralSettingsForm', () => {
  it('saves only the changed colour and never claims success itself', async () => {
    const wrapper = mount(GeneralSettingsForm, {
      props: { settings: { title: 'JF', slug: 'JF', logo_url: '', brand_color: '#b91c1c' }, canEdit: true },
      global,
    })
    await wrapper.findAll('[role="radio"]')[4]!.trigger('click')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('save')?.[0]).toEqual([{ brand_color: '#0f766e' }])
    expect(wrapper.text()).not.toContain('erfolgreich gespeichert')
  })
})
