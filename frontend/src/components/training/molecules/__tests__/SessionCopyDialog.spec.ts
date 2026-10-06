import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SessionCopyDialog from '../SessionCopyDialog.vue'

const api = vi.hoisted(() => ({ copy: vi.fn(), saveAsTemplate: vi.fn() }))
vi.mock('@/api/training', () => ({ trainingSessionsApi: api }))

const stubs = {
  Dialog: { template: '<div><slot /></div>' },
  Button: { props: ['label', 'disabled', 'type'], template: '<button :type="type || \'button\'" :disabled="disabled">{{ label }}</button>' },
  InputText: { props: ['modelValue', 'id'], emits: ['update:modelValue'], template: '<input :id="id" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
}

function mountDialog(mode: 'copy' | 'template') {
  return mount(SessionCopyDialog, {
    props: { visible: true, mode, session: { id: 4, title: 'Knotenabend', date: '2099-03-01' } },
    global: { stubs },
  })
}

describe('SessionCopyDialog', () => {
  beforeEach(() => {
    api.copy.mockReset()
    api.saveAsTemplate.mockReset()
  })

  it('copies to an explicit date and reports the new session', async () => {
    api.copy.mockResolvedValue({ data: { id: 9 } })
    const wrapper = mountDialog('copy')
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    await wrapper.find('#copy-date').setValue('2099-05-01')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(api.copy).toHaveBeenCalledWith(4, { date: '2099-05-01', title: 'Knotenabend' })
    expect(wrapper.emitted('copied')).toEqual([[{ id: 9 }]])
  })

  it('saves a template under the chosen name and keeps errors visible', async () => {
    api.saveAsTemplate.mockRejectedValueOnce({ response: { data: { detail: 'Keine Berechtigung.' } } })
    api.saveAsTemplate.mockResolvedValueOnce({ data: { id: 3 } })
    const wrapper = mountDialog('template')
    expect(wrapper.find('#copy-date').exists()).toBe(false)
    await wrapper.find('#copy-title').setValue('Knoten-Vorlage')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Berechtigung.')
    expect(wrapper.emitted('update:visible')).toBeUndefined()
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(api.saveAsTemplate).toHaveBeenLastCalledWith(4, { title: 'Knoten-Vorlage' })
    expect(wrapper.emitted('saved')).toEqual([[{ id: 3 }]])
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
  })
})
