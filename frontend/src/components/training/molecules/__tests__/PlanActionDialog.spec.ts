import { describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Select from 'primevue/select'
import PlanActionDialog from '../PlanActionDialog.vue'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'

vi.mock('@/api/training', () => ({ trainingSessionsApi: { plan: async () => ({ data: {
  id: 1, revision: 1, title: 'Plan', date: '2030-01-01', start_time: '18:00:00', end_time: '20:00:00',
  description: '', notes: '', location: '', groups: [], department: 1, recurrence_rule: null,
  blocks: [0, 30].map((offset, index) => ({
    id: index + 1, title: `Block ${index + 1}`, session: 1, groups: [], content: '',
    duration_minutes: 15, start_offset_minutes: offset, position_order: 0,
    library_block: null, color: '', nextcloud_folder_url: '', media: [], attachments: [],
  })),
} }) } }))

describe('reviewing a plan operation', () => {
  it('shows the full preview and stages both moves only on explicit acceptance', async () => {
    setActivePinia(createPinia())
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    const wrapper = mount(PlanActionDialog, {
      props: { visible: true, duration: 120 }, global: { renderStubDefaultSlot: true,
        stubs: { Select: true, InputNumber: true, Button: {
          props: ['label', 'disabled'], emits: ['click'], template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>',
        }, Dialog: { template: '<div><slot /><slot name="footer" /></div>' } },
      },
    })
    const selectors = wrapper.findAllComponents(Select)
    selectors[1]!.vm.$emit('update:modelValue', 1)
    selectors[2]!.vm.$emit('update:modelValue', 2)
    await flushPromises()
    expect(wrapper.find('table').text()).toContain('0 → 30')
    expect(wrapper.find('table').text()).toContain('30 → 0')
    expect(store.isDirty).toBe(false)
    const apply = wrapper.findAll('button').find((button) => button.text() === 'Vorschau übernehmen')!
    await apply.trigger('click')
    expect(store.blocks.map((b) => b.start_offset_minutes)).toEqual([30, 0])
    expect(store.isDirty).toBe(true)
    store.undo()
    expect(store.blocks.map((b) => b.start_offset_minutes)).toEqual([0, 30])
    expect(store.canUndo).toBe(false)
    wrapper.unmount()
  })
})
