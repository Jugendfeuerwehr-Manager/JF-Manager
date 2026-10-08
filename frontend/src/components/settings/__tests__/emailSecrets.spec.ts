import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EmailSettingsForm from '../molecules/EmailSettingsForm.vue'
const settings = {
  email_host: 'smtp.example.org',
  email_port: 587,
  email_use_tls: true,
  email_use_ssl: false,
  email_host_user: 'synthetic',
  default_from_email: 'synthetic@example.org',
  has_email_host_password: true,
  email_credentials_unavailable: true,
}
const field = {
  props: ['modelValue', 'fieldId', 'label'],
  emits: ['update:modelValue'],
  template:
    '<label>{{ label }}<input :id="fieldId" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)"></label>',
}
const checkbox = {
  props: ['modelValue', 'fieldId', 'label'],
  emits: ['update:modelValue'],
  template:
    '<label>{{ label }}<input :id="fieldId" type="checkbox" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)"></label>',
}
function render() {
  return mount(EmailSettingsForm, {
    props: { settings, canEdit: true },
    global: {
      stubs: {
        SettingsCategoryCard: { template: '<div><slot /><slot name="footer" /></div>' },
        SettingsTextField: field,
        SettingsNumberField: field,
        SettingsCheckbox: checkbox,
        Button: { template: '<button />' },
        Message: { template: '<p><slot /></p>' },
      },
    },
  })
}
describe('SMTP secret editing', () => {
  it('preserves an omitted password during unrelated edits and explains the recovery', async () => {
    const wrapper = render()
    expect(wrapper.text()).toContain('Versand ist gesperrt')
    await wrapper.get('#email_host').setValue('new.example.org')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('save')?.[0]).toEqual([{ email_host: 'new.example.org' }])
    expect(wrapper.text()).not.toContain('erfolgreich gespeichert')
  })
  it('allows explicit replacement or removal without revealing stored values', async () => {
    const wrapper = render()
    expect((wrapper.get('#email_host_password').element as HTMLInputElement).value).toBe('')
    await wrapper.get('#email_host_password').setValue('synthetic-replacement')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('save')?.[0]).toEqual([{ email_host_password: 'synthetic-replacement' }])
    await wrapper.get('#clear-smtp-password').setValue(true)
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('save')?.[1]).toEqual([{ email_host_password: '' }])
  })
})
