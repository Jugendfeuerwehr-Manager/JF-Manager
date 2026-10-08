import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AutoComplete from 'primevue/autocomplete'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import BlockResourcesFields from '../BlockResourcesFields.vue'
import type { BlockMaterial } from '@/types/training'

const api = vi.hoisted(() => ({ instructorOptions: vi.fn(), materialOptions: vi.fn() }))
vi.mock('@/api/training', () => ({ trainingSessionsApi: api }))

const jacket = { id: 5, name: 'Jacke', unit: 'Stück', variants: [{ id: 9, label: 'Jacke (größe: 164)' }] }

function mountFields(materials: BlockMaterial[] = []) {
  return mount(BlockResourcesFields, {
    props: { sessionId: 1, instructors: [{ id: 3, name: 'Ehemals Ausbilder' }], materials },
    global: { stubs: { AutoComplete: true, MultiSelect: true, Select: true, InputNumber: true, Message: true,
      Button: { props: ['label', 'ariaLabel'], emits: ['click'], template: '<button :aria-label="ariaLabel" @click="$emit(\'click\')">{{ label }}</button>' } } },
  })
}

describe('BlockResourcesFields', () => {
  beforeEach(() => {
    api.instructorOptions.mockReset().mockResolvedValue({ data: [{ id: 7, name: 'Alex Ausbilder' }] })
    api.materialOptions.mockReset().mockResolvedValue({ data: [jacket] })
  })

  it('offers eligible instructors and keeps saved ones visible', async () => {
    const wrapper = mountFields()
    await flushPromises()
    const select = wrapper.findComponent(MultiSelect)
    expect(api.instructorOptions).toHaveBeenCalledWith(1)
    select.vm.$emit('update:modelValue', [7, 3])
    expect(wrapper.emitted('update:instructors')).toEqual([[[{ id: 7, name: 'Alex Ausbilder' }, { id: 3, name: 'Ehemals Ausbilder' }]]])
  })

  it('adds rows, searches items and syncs the label with the chosen variant', async () => {
    const wrapper = mountFields()
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('update:materials')![0]).toEqual([[{ item: null, variant: null, quantity: 1, label: '' }]])
    await wrapper.setProps({ materials: [{ item: null, variant: null, quantity: 1, label: '' }] })
    const auto = wrapper.findComponent(AutoComplete)
    auto.vm.$emit('complete', { query: 'jac' })
    await flushPromises()
    expect(api.materialOptions).toHaveBeenCalledWith(1, 'jac')
    auto.vm.$emit('update:modelValue', jacket)
    const chosen = wrapper.emitted('update:materials')!.at(-1)![0] as BlockMaterial[]
    expect(chosen).toEqual([{ item: 5, variant: null, quantity: 1, label: 'Jacke' }])
    await wrapper.setProps({ materials: chosen })
    wrapper.findComponent(Select).vm.$emit('update:modelValue', 9)
    expect(wrapper.emitted('update:materials')!.at(-1)![0]).toEqual([{ item: 5, variant: 9, quantity: 1, label: 'Jacke (größe: 164)' }])
  })

  it('keeps free text as label without an item', async () => {
    const wrapper = mountFields([{ item: null, variant: null, quantity: 1, label: '' }])
    wrapper.findComponent(AutoComplete).vm.$emit('update:modelValue', 'Kreide')
    expect(wrapper.emitted('update:materials')!.at(-1)![0]).toEqual([{ item: null, variant: null, quantity: 1, label: 'Kreide' }])
  })
})
