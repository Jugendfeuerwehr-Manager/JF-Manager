import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import FormRenderer from '../FormRenderer.vue'
import type { FormSchema } from '@/types/admissions'

const schema: FormSchema = {
  pages: [
    {
      id: 'p',
      title: 'Personalien',
      sections: [
        {
          id: 's',
          title: '',
          elements: [
            { id: 'b', type: 'date', key: 'geburtsdatum', label: 'Geburtsdatum', target: 'member.birthday' },
            { id: 'g', type: 'text', key: 'eltern_hinweis', label: 'Nur für Minderjährige', visible_if: { age_below: 18 } },
            { id: 'x', type: 'select', key: 'geschlecht', label: 'Geschlecht', target: 'member.gender' }
          ]
        }
      ]
    }
  ]
}

describe('FormRenderer', () => {
  it('hides age-bound elements for adults and offers the gender options', () => {
    const adult = mount(FormRenderer, { props: { schema, modelValue: { geburtsdatum: '1990-01-01' } } })
    expect(adult.text()).not.toContain('Nur für Minderjährige')
    expect(adult.findAll('option').map((o) => o.text())).toEqual(['Bitte wählen', 'Männlich', 'Weiblich', 'Divers'])

    const child = mount(FormRenderer, { props: { schema, modelValue: { geburtsdatum: '2015-01-01' } } })
    expect(child.text()).toContain('Nur für Minderjährige')
  })

  it('emits answers by key', async () => {
    const wrapper = mount(FormRenderer, { props: { schema, modelValue: {} } })
    await wrapper.find('input[type="date"]').setValue('2014-03-02')
    expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toEqual({ geburtsdatum: '2014-03-02' })
  })
})
