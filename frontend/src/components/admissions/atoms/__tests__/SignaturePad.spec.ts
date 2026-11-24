import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SignaturePad from '../SignaturePad.vue'

const PNG = 'data:image/png;base64,iVBORw0KGgo='

describe('SignaturePad', () => {
  it('shows a signature that arrives after mounting when read-only', async () => {
    // The review loads the sealed images after the form is already on screen.
    const wrapper = mount(SignaturePad, { props: { label: 'Unterschrift', disabled: true, modelValue: '' } })
    expect(wrapper.text()).toContain('Nicht unterschrieben')
    await wrapper.setProps({ modelValue: PNG })
    expect(wrapper.get('img').attributes('src')).toBe(PNG)
    expect(wrapper.find('canvas').exists()).toBe(false)
  })
})
