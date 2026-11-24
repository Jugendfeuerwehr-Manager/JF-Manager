import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import MemberLeaveDialog from '../MemberLeaveDialog.vue'
import { toIsoDateLocal } from '@/utils/dateParsing'

const statuses = [
  { id: 1, name: 'Aktiv', color: '#000', category: 'active', department: null, sort_order: 0 },
  { id: 4, name: 'Ehemalige', color: '#999', category: 'left', department: null, sort_order: 1 },
  { id: 6, name: 'Übertritt EA', color: '#999', category: 'transferred', department: null, sort_order: 2 },
] as never

function mountDialog(props: Record<string, unknown> = {}) {
  return mount(MemberLeaveDialog, {
    props: { modelValue: false, memberName: 'Mia Muster', joined: '2020-04-01', statuses, ...props },
    global: { plugins: [PrimeVue], stubs: { Dialog: { template: '<div><slot /></div>' }, DatePicker: true, Select: true } },
  })
}

describe('MemberLeaveDialog', () => {
  it('suggests today and the former-member status, and explains what follows', async () => {
    const wrapper = mountDialog()
    await wrapper.setProps({ modelValue: true })
    expect(wrapper.text()).toContain('Was danach passiert')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('confirm')?.[0]?.[0]).toEqual({
      left_at: toIsoDateLocal(new Date()),
      kind: 'exit_other',
      exit_reason: '',
      status_id: 4,
    })
  })

  it('a transfer to the Einsatzabteilung suggests the transferred stage and drops the reason', async () => {
    const wrapper = mountDialog()
    await wrapper.setProps({ modelValue: true })
    const vm = wrapper.vm as unknown as { kind: string; exitReason: string | null }
    vm.exitReason = 'school'
    vm.kind = 'exit_ea'
    await wrapper.vm.$nextTick()
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('confirm')?.[0]?.[0]).toMatchObject({ kind: 'exit_ea', exit_reason: '', status_id: 6 })
  })

  it('falls back to the stage name while categories are not set up', async () => {
    const legacy = [{ id: 1, name: 'Aktiv', category: 'active' }, { id: 4, name: 'Ausgetreten', category: 'active' }]
    const wrapper = mountDialog({ statuses: legacy })
    await wrapper.setProps({ modelValue: true })
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('confirm')?.[0]?.[0]).toMatchObject({ status_id: 4 })
  })

  it('refuses a leave before joining', async () => {
    const wrapper = mountDialog()
    await wrapper.setProps({ modelValue: true })
    ;(wrapper.vm as unknown as { leftAt: Date }).leftAt = new Date('2019-12-31T00:00:00')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('confirm')).toBeUndefined()
    expect(wrapper.text()).toContain('Der Austritt kann nicht vor dem Eintritt liegen.')
  })
})
