import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import TrainingTemplatesDialog from '../TrainingTemplatesDialog.vue'

const api = vi.hoisted(() => ({ list: vi.fn(), instantiate: vi.fn(), delete: vi.fn() }))
vi.mock('@/api/training', () => ({ trainingTemplatesApi: api }))

const template = {
  id: 3, title: 'Knoten-Vorlage', description: 'Grundlagen', start_time: '18:00:00', end_time: '20:00:00',
  location: 'Gerätehaus', department: 1, groups: [], block_count: 4, source_session: null,
  created_by_name: null, created_at: '', updated_at: '',
}

function mountDialog(defaultDate: string | null = null) {
  return mount(TrainingTemplatesDialog, {
    props: { visible: true, defaultDate, department: 1 },
    global: {
      stubs: {
        Dialog: { template: '<div><slot /><slot name="footer" /></div>' },
        Button: { props: ['label', 'disabled', 'ariaLabel'], emits: ['click'], template: '<button :aria-label="ariaLabel" :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>' },
        InputText: { props: ['modelValue', 'id'], emits: ['update:modelValue'], template: '<input :id="id" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
      },
    },
  })
}

describe('TrainingTemplatesDialog', () => {
  beforeEach(() => {
    api.list.mockReset().mockResolvedValue({ data: { results: [template] } })
    api.instantiate.mockReset()
    api.delete.mockReset()
  })

  it('creates an exercise only with a date and emits the new draft', async () => {
    api.instantiate.mockResolvedValue({ data: { id: 11 } })
    const wrapper = mountDialog()
    await flushPromises()
    expect(api.list).toHaveBeenCalledWith({ limit: 500, department: 1 })
    expect(wrapper.text()).toContain('18:00–20:00 · 4 Bausteine · Gerätehaus')
    const create = wrapper.findAll('button').find((b) => b.text() === 'Übung anlegen')!
    expect(create.attributes('disabled')).toBeDefined()
    await wrapper.find('#template-date').setValue('2099-04-01')
    await create.trigger('click')
    await flushPromises()
    expect(api.instantiate).toHaveBeenCalledWith(3, { date: '2099-04-01' })
    expect(wrapper.emitted('created')).toEqual([[{ id: 11 }]])
  })

  it('deletes only after confirmation', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true)
    api.delete.mockResolvedValue({})
    const wrapper = mountDialog('2099-04-01')
    await flushPromises()
    const remove = wrapper.find('button[aria-label="Vorlage Knoten-Vorlage löschen"]')
    await remove.trigger('click')
    expect(api.delete).not.toHaveBeenCalled()
    await remove.trigger('click')
    await flushPromises()
    expect(api.delete).toHaveBeenCalledWith(3)
    expect(wrapper.text()).toContain('Keine Vorlagen gefunden.')
    confirm.mockRestore()
  })
})
