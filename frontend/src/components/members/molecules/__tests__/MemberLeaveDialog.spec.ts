import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import MemberLeaveDialog from '../MemberLeaveDialog.vue'
import { toIsoDateLocal } from '@/utils/dateParsing'

const statuses = [{ id: 1, name: 'Aktiv', color: '#000' }, { id: 4, name: 'Ausgetreten', color: '#999' }] as never

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
    expect(wrapper.emitted('confirm')?.[0]?.[0]).toEqual({ left_at: toIsoDateLocal(new Date()), status_id: 4 })
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
