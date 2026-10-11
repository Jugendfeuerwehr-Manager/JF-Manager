import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import QuickReturnDialog from '../QuickReturnDialog.vue'

const { store, toastAdd } = vi.hoisted(() => ({
  store: {
    memberLoans: [
      {
        member_id: 42,
        member_name: 'Mia Beispiel',
        location_id: 9,
        total_items: 2,
        items: [
          { stock_id: 1, item_id: 5, item_name: 'Helm', variant_id: null, variant_display: null, quantity: 1 },
          { stock_id: 2, item_id: 6, item_name: 'Jacke', variant_id: 61, variant_display: 'Jacke · 152', quantity: 3 },
        ],
      },
    ],
    storageLocations: [{ id: 3, name: 'Lager', full_path: 'Lager' }],
    batchReturn: vi.fn(),
  },
  toastAdd: vi.fn(),
}))

vi.mock('@/stores/inventory', () => ({ useInventoryStore: () => store }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: toastAdd }) }))

function render() {
  return mount(QuickReturnDialog, {
    props: { modelValue: false, preselectedMember: 9 },
    global: {
      stubs: {
        Dialog: { template: '<div><slot /><slot name="footer" /></div>' },
        Dropdown: true,
        Tag: true,
        InputText: true,
        InputNumber: {
          props: ['modelValue', 'max'],
          emits: ['update:modelValue'],
          template: '<input class="qty" type="number" :value="modelValue" @input="$emit(\'update:modelValue\', Number($event.target.value))" />',
        },
        Button: {
          props: ['label', 'disabled'],
          emits: ['click'],
          template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>',
        },
      },
    },
  })
}

describe('QuickReturnDialog (UX-05.1)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    store.batchReturn.mockResolvedValue({ transactions: [], returned_quantity: 3 })
  })

  it('takes back part quantities of several articles in one booking', async () => {
    const wrapper = render()
    await wrapper.setProps({ modelValue: true })
    const submit = () => wrapper.findAll('button').find((b) => b.text() === 'Zurückgeben')!
    expect(submit().attributes('disabled')).toBeDefined()

    const inputs = wrapper.findAll('input.qty')
    await inputs[0]!.setValue('1')
    await inputs[1]!.setValue('2')
    expect(wrapper.text()).toContain('3 Stück aus 2 Artikeln werden zurückgenommen.')

    await submit().trigger('click')
    await flushPromises()
    expect(store.batchReturn).toHaveBeenCalledWith({
      member: 42,
      items: [
        { item: 5, item_variant: null, quantity: 1, target: 3 },
        { item: null, item_variant: 61, quantity: 2, target: 3 },
      ],
      note: '',
    })
    expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'success' }))
  })

  it('shows the server reason when the booking is refused', async () => {
    store.batchReturn.mockRejectedValueOnce({ response: { status: 400, data: { detail: 'Jacke · 152: nur noch 1 ausgegeben.' } } })
    const wrapper = render()
    await wrapper.setProps({ modelValue: true })
    const allButtons = wrapper.findAll('button').filter((b) => b.text() === 'Alles')
    await allButtons[1]!.trigger('click')
    await wrapper.findAll('button').find((b) => b.text() === 'Zurückgeben')!.trigger('click')
    await flushPromises()
    expect(toastAdd).toHaveBeenCalledWith(expect.objectContaining({ severity: 'error', detail: 'Jacke · 152: nur noch 1 ausgegeben.' }))
  })
})
