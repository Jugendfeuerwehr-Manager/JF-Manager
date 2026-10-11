import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import QuickLoanDialogV2 from '../QuickLoanDialogV2.vue'

const { store } = vi.hoisted(() => ({
  store: {
    items: [{ id: 6, name: 'Jacke', is_variant_parent: true, variants: [{ id: 61, sku: 'J-152', variant_attributes: { Größe: '152' } }] }],
    stocks: [{ item: null, item_variant: 61, location: 3, quantity: 4 }],
    locations: [{ id: 3, is_member: false }],
    lookupCode: vi.fn(),
    fetchAvailability: vi.fn(),
    batchLoan: vi.fn(),
  },
}))

vi.mock('@/stores/inventory', () => ({ useInventoryStore: () => store }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))
vi.mock('@/composables/useRoleMemberOptions', () => ({
  useRoleMemberOptions: () => ({ members: ref([]), error: ref(''), load: vi.fn() }),
}))

function render() {
  return mount(QuickLoanDialogV2, {
    props: { modelValue: true },
    global: {
      stubs: {
        Dialog: { template: '<div><slot /><slot name="footer" /></div>' },
        Dropdown: true,
        InputNumber: true,
        Message: true,
        Tag: { props: ['value'], template: '<span>{{ value }}</span>' },
        InputText: {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
        },
        Button: { props: ['label', 'type', 'disabled'], template: '<button :type="type || \'button\'" :disabled="disabled">{{ label }}</button>' },
      },
    },
  })
}

describe('QuickLoanDialogV2 code entry (UX-05.1)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    store.fetchAvailability.mockResolvedValue({ can_view_orders: true, results: [{ item: 6, item_variant: 61, available: 4, issued: 2, ordered: 5 }] })
  })

  it('selects article and size from a typed code and shows issued and ordered', async () => {
    store.lookupCode.mockResolvedValue([{ item: 6, item_variant: 61, label: 'Jacke · 152', is_variant_parent: false }])
    const wrapper = render()
    await wrapper.get('#loan-code').setValue('J-152')
    await wrapper.get('form.code-lookup').trigger('submit')
    await flushPromises()
    expect(store.lookupCode).toHaveBeenCalledWith('J-152')
    expect(wrapper.text()).toContain('Jacke · 152 hinzugefügt.')
    expect(wrapper.text()).toContain('4 verfügbar')
    expect(wrapper.text()).toContain('2 ausgegeben · 5 bestellt')
  })

  it('asks for a more precise code when several articles match', async () => {
    store.lookupCode.mockResolvedValue([
      { item: 6, item_variant: 61, label: 'Jacke · 152', is_variant_parent: false },
      { item: 7, item_variant: null, label: 'Helm', is_variant_parent: false },
    ])
    const wrapper = render()
    await wrapper.get('#loan-code').setValue('1')
    await wrapper.get('form.code-lookup').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('2 Treffer – bitte genauer eingeben.')
  })
})
