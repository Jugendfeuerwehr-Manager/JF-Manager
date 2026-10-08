import { describe, expect, it, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DebriefDialog from '../DebriefDialog.vue'

const stored = {
  actual_start: null, actual_end: null, actual_minutes: null, reflection: '', improvements: '', revision: 0,
  updated_by_name: null, updated_at: null, planned_minutes: 120, session_status: 'published', session_revision: 3,
}
const api = vi.hoisted(() => ({ debrief: vi.fn(), saveDebrief: vi.fn() }))
vi.mock('@/api/training', () => ({ trainingSessionsApi: api }))

const stubs = {
  Dialog: { template: '<div><slot /><slot name="footer" /></div>' },
  Button: { props: ['label', 'disabled'], emits: ['click'], template: '<button type="button" :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>' },
  Textarea: { props: ['modelValue', 'id'], emits: ['update:modelValue'], template: '<textarea :id="id" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
  Checkbox: { props: ['modelValue', 'inputId'], emits: ['update:modelValue'], template: '<input type="checkbox" :id="inputId" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" />' },
  Message: { template: '<p role="alert"><slot /></p>' },
}
const session = { id: 4, status: 'published' as const, start_time: '18:00:00', end_time: '20:00:00', linked_service_id: 9 }
const button = (w: ReturnType<typeof mount>, label: string) => w.findAll('button').find((b) => b.text() === label)!

describe('DebriefDialog', () => {
  beforeEach(() => { api.debrief.mockReset(); api.saveDebrief.mockReset() })

  it('compares actual with planned time and can complete the exercise', async () => {
    api.debrief.mockResolvedValue({ data: stored })
    api.saveDebrief.mockResolvedValue({ data: { ...stored, revision: 1, session_status: 'completed' } })
    const wrapper = mount(DebriefDialog, { props: { visible: true, session }, global: { stubs } })
    await flushPromises()
    await button(wrapper, 'Planzeit übernehmen').trigger('click')
    await wrapper.find('#debrief-end').setValue('20:15')
    expect(wrapper.text()).toContain('Geplant 18:00–20:00 (120 Min.) · tatsächlich 135 Min. (+15)')
    await wrapper.find('#debrief-reflection').setValue('Gut')
    await wrapper.find('#debrief-complete').setValue(true)
    await button(wrapper, 'Speichern').trigger('click')
    await flushPromises()
    expect(api.saveDebrief).toHaveBeenCalledWith(4, {
      expected_revision: 0, actual_start: '18:00', actual_end: '20:15', reflection: 'Gut', improvements: '', complete: true,
    })
    expect(wrapper.emitted('saved')![0]![0]).toMatchObject({ session_status: 'completed' })
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
  })

  it('keeps own input on a conflict and saves it against the newer version on request', async () => {
    api.debrief.mockResolvedValue({ data: stored })
    api.saveDebrief
      .mockRejectedValueOnce({ response: { status: 409, data: { current: { ...stored, revision: 2, reflection: 'Fremd', updated_by_name: 'Pia Planer' } } } })
      .mockResolvedValueOnce({ data: { ...stored, revision: 3, reflection: 'Meins' } })
    const wrapper = mount(DebriefDialog, { props: { visible: true, session }, global: { stubs } })
    await flushPromises()
    await wrapper.find('#debrief-reflection').setValue('Meins')
    await button(wrapper, 'Speichern').trigger('click')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('von Pia Planer')
    expect(wrapper.text()).toContain('Reflexion: Fremd')
    expect((wrapper.find('#debrief-reflection').element as HTMLTextAreaElement).value).toBe('Meins')
    await button(wrapper, 'Meine Eingaben speichern').trigger('click')
    await flushPromises()
    expect(api.saveDebrief.mock.calls[1]![1]).toMatchObject({ expected_revision: 2, reflection: 'Meins' })
  })

  it('rejects a one-sided or reversed actual time without asking the server', async () => {
    api.debrief.mockResolvedValue({ data: stored })
    const wrapper = mount(DebriefDialog, { props: { visible: true, session: { ...session, status: 'completed' } }, global: { stubs } })
    await flushPromises()
    expect(wrapper.find('#debrief-complete').exists()).toBe(false)
    await wrapper.find('#debrief-start').setValue('19:00')
    await button(wrapper, 'Speichern').trigger('click')
    expect(wrapper.text()).toContain('gemeinsam angeben')
    await wrapper.find('#debrief-end').setValue('18:00')
    await button(wrapper, 'Speichern').trigger('click')
    expect(wrapper.text()).toContain('nach dem Beginn')
    expect(api.saveDebrief).not.toHaveBeenCalled()
  })
})
