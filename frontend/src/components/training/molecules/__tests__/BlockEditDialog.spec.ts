import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import BlockEditDialog from '../BlockEditDialog.vue'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'

vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))

const station = (id: number, group: { id: number; name: string }, key: string | null) => ({
  id, title: 'Knotenkunde', session: 1, groups: [group], content: '<p>Ablauf</p>', duration_minutes: 25,
  start_offset_minutes: 15 + (id - 1) * 30, position_order: 0, library_block: null, library_block_title: null,
  color: '', nextcloud_folder_url: '', media: [], attachments: [], kind: 'station', station_key: key,
})

vi.mock('@/api/training', () => ({
  trainingSessionsApi: {
    plan: async () => ({ data: {
      id: 1, revision: 1, status: 'draft', can_manage_plan: true, title: 'Plan', date: '2030-01-01',
      start_time: '18:00:00', end_time: '20:00:00', description: '', notes: '', location: '', department: 1,
      groups: [{ id: 1, name: 'Bambini' }, { id: 2, name: 'Jugend' }], recurrence_rule: null,
      blocks: [station(1, { id: 1, name: 'Bambini' }, 'k1'), station(2, { id: 2, name: 'Jugend' }, 'k1')],
    } }),
    instructorOptions: async () => ({ data: [] }),
  },
  libraryApi: { get: vi.fn() },
}))

const stubs = {
  Dialog: { template: '<div><slot /><slot name="footer" /></div>' },
  Button: { props: ['label'], emits: ['click'], template: '<button @click="$emit(\'click\')">{{ label }}</button>' },
  Checkbox: { props: ['modelValue', 'inputId'], emits: ['update:modelValue'], template: '<input type="checkbox" :id="inputId" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" />' },
  InputText: true, InputNumber: true, MultiSelect: true, Select: true, Textarea: true,
  BlockEditor: true, AssetPanel: true, BlockResourcesFields: true,
}

async function open(blockId: number) {
  setActivePinia(createPinia())
  const store = useTrainingPlannerStore()
  await store.loadBlocks(1)
  const block = store.blocks.find((b) => b.id === blockId)!
  const wrapper = mount(BlockEditDialog, { props: { visible: true, block }, global: { stubs, directives: { tooltip: {} } } })
  await flushPromises()
  return { store, wrapper }
}

describe('BlockEditDialog linked stations', () => {
  it('names the linked groups and detaches only this block on request', async () => {
    const { store, wrapper } = await open(1)
    expect(wrapper.find('[role="note"]').text()).toContain('gelten auch für Jugend')
    const update = vi.spyOn(store, 'updateBlockContent')
    await wrapper.find('#block-detach').setValue(true)
    await wrapper.findAll('button').find((b) => b.text() === 'Übernehmen')!.trigger('click')
    await flushPromises()
    expect(update.mock.calls[0]![1]).toMatchObject({ station_key: null })
    expect(store.blocks.find((b) => b.id === 1)!.station_key).toBeNull()
    expect(store.blocks.find((b) => b.id === 2)!.station_key).toBe('k1')
  })

  it('keeps the link by default', async () => {
    const { store, wrapper } = await open(2)
    const update = vi.spyOn(store, 'updateBlockContent')
    await wrapper.findAll('button').find((b) => b.text() === 'Übernehmen')!.trigger('click')
    await flushPromises()
    expect(update.mock.calls[0]![1]).not.toHaveProperty('station_key')
  })
})
