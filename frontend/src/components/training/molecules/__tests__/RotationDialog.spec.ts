import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import RotationDialog from '../RotationDialog.vue'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'

vi.mock('@/api/training', () => ({
  trainingSessionsApi: {
    instructorOptions: async () => ({ data: [{ id: 7, name: 'Alex Ausbilder' }] }),
    plan: async () => ({ data: {
      id: 1, revision: 1, status: 'draft', can_manage_plan: true, title: 'Plan', date: '2030-01-01',
      start_time: '18:00:00', end_time: '20:00:00', description: '', notes: '', location: '', department: 1,
      groups: [{ id: 1, name: 'Rot' }, { id: 2, name: 'Blau' }, { id: 3, name: 'Grün' }], recurrence_rule: null,
      blocks: [{ id: 5, title: 'Begrüßung', session: 1, groups: [], content: '', duration_minutes: 10, start_offset_minutes: 0,
        position_order: 0, library_block: null, library_block_title: null, color: '', nextcloud_folder_url: '', media: [], attachments: [] }],
    } }),
  },
  libraryApi: { get: vi.fn() },
}))

const stubs = {
  Dialog: { template: '<div><slot /><slot name="footer" /></div>' },
  Button: { props: ['label', 'disabled', 'ariaLabel'], emits: ['click'], template: '<button :aria-label="ariaLabel" :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>' },
  InputText: { props: ['modelValue'], emits: ['update:modelValue'], template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
  InputNumber: true, MultiSelect: true, Select: true, Message: { template: '<p role="alert"><slot /></p>' },
}

describe('RotationDialog', () => {
  it('previews the full rotation after the existing plan and applies it as one undo step', async () => {
    setActivePinia(createPinia())
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    const wrapper = mount(RotationDialog, { props: { visible: true, duration: 120 }, global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('3 Runden · 18:10–19:20')
    expect(text).toContain('1 · 18:10–18:30')
    expect(text).toContain('Wechsel 18:30–18:35')
    // Station 2 for group 1 in round 2; every group sees all three.
    expect(wrapper.findAll('tbody tr')[2]!.text()).toContain('Station 2')
    await wrapper.findAll('button').find((b) => b.text() === 'In den Entwurf übernehmen')!.trigger('click')
    await flushPromises()
    expect(store.blocks.filter((b) => b.kind === 'station')).toHaveLength(9)
    expect(store.blocks.filter((b) => b.kind === 'transition')).toHaveLength(2)
    expect(wrapper.emitted('update:visible')).toEqual([[false]])
    store.undo()
    expect(store.blocks).toHaveLength(1)
  })

  it('blocks adoption with a readable reason when the frame is exceeded', async () => {
    setActivePinia(createPinia())
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    const wrapper = mount(RotationDialog, { props: { visible: true, duration: 60 }, global: { stubs } })
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('endet nach 80 Minuten')
    expect(wrapper.findAll('button').find((b) => b.text() === 'In den Entwurf übernehmen')!.attributes('disabled')).toBeDefined()
  })
})
