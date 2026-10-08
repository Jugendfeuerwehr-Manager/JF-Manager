import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PublishJustificationDialog from '../PublishJustificationDialog.vue'

describe('PublishJustificationDialog', () => {
  it('lists warnings and confirms only with a justification', async () => {
    const wrapper = mount(PublishJustificationDialog, {
      props: { visible: true, warnings: ['Ort „hof“ gleichzeitig belegt'] },
      global: { stubs: {
        Dialog: { template: '<div><slot /></div>' },
        Textarea: { props: ['modelValue', 'id'], emits: ['update:modelValue'], template: '<textarea :id="id" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
        Button: { props: ['label', 'disabled', 'type'], template: '<button :type="type || \'button\'" :disabled="disabled">{{ label }}</button>' },
      } },
    })
    expect(wrapper.text()).toContain('Ort „hof“ gleichzeitig belegt')
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('confirm')).toBeUndefined()
    await wrapper.find('#publish-justification').setValue('  Bewusst gemeinsamer Auftakt ')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('confirm')).toEqual([['Bewusst gemeinsamer Auftakt']])
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
  })
})
