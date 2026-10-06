import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PermissionPicker from '../PermissionPicker.vue'

const permissions = ['members.view_member', 'members.add_member', 'members.change_member', 'members.delete_member', 'members.can_send_member_emails', 'custom.unrecognised'].map(full_codename => ({ full_codename }))
function render(value: string[] = [], disabled = false) {
  return mount(PermissionPicker, { props: { modelValue: value, permissions, disabled } })
}
describe('PermissionPicker', () => {
  it('selects all editing rights plus reading without granting deletion or special actions', async () => {
    const wrapper = render(['custom.unrecognised'])
    await wrapper.findAll('button').find(button => button.text() === 'Alle anlegen und bearbeiten')!.trigger('click')
    const selection = wrapper.emitted('update:modelValue')![0]![0] as string[]
    expect(selection).toEqual(expect.arrayContaining(['custom.unrecognised', 'members.view_member', 'members.add_member', 'members.change_member']))
    expect(selection).not.toContain('members.delete_member')
    expect(selection).not.toContain('members.can_send_member_emails')
  })
  it('retains reading and unknown permissions when editing is removed', async () => {
    const wrapper = render(['members.view_member', 'members.add_member', 'members.change_member', 'custom.unrecognised'])
    await wrapper.get('.permission-row').findAll('input')[1]!.setValue(false)
    expect(wrapper.emitted('update:modelValue')![0]![0]).toEqual(['members.view_member', 'custom.unrecognised'])
  })
  it('indicates partial editing accurately without treating reading alone as partial editing', () => {
    const wrapper = render(['members.view_member', 'members.add_member'])
    expect((wrapper.get('.permission-row').findAll('input')[1]!.element as HTMLInputElement).indeterminate).toBe(true)
    const readOnly = render(['members.view_member'])
    expect((readOnly.get('.permission-row').findAll('input')[1]!.element as HTMLInputElement).indeterminate).toBe(false)
  })
  it('searches by familiar task names and keeps technical identifiers inside a collapsed advanced view', async () => {
    const wrapper = render()
    expect(wrapper.get('.permission-area').text()).toContain('Mitglieder')
    expect(wrapper.get('.permission-area').text()).not.toContain('members.view_member')
    expect(wrapper.get('details').attributes('open')).toBeUndefined()
    await wrapper.get('input[type="search"]').setValue('Bestellungen')
    expect(wrapper.findAll('.permission-area')).toHaveLength(0)
  })
  it('disables every input and bulk action for archived or read-only roles', () => {
    const wrapper = render([], true)
    expect(wrapper.findAll('input[type="checkbox"], button').every(element => element.attributes('disabled') !== undefined)).toBe(true)
  })
})
