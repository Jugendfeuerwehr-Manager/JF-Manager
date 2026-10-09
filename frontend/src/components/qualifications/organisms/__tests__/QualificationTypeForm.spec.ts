import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import { createPinia, setActivePinia } from 'pinia'
import QualificationTypeForm from '../QualificationTypeForm.vue'
import { useQualificationsStore } from '@/stores/qualifications'
import type { QualificationType } from '@/types/qualifications'

const MultiSelectStub = {
  props: ['modelValue', 'options'],
  emits: ['update:modelValue'],
  template: '<div class="ms" :data-options="options.map((o) => o.label).join(\'|\')" />',
}

const type = (id: number, name: string, includes: number[] = []): QualificationType => ({
  id, name, expires: false, validity_period: null, description: '', includes,
})

function mountForm(initialData?: QualificationType) {
  setActivePinia(createPinia())
  const store = useQualificationsStore()
  vi.spyOn(store, 'fetchQualificationTypes').mockImplementation(async () => {
    store.qualificationTypes = [type(1, 'Truppmann'), type(2, 'Truppführer', [1]), type(3, 'Gruppenführer')]
    return store.qualificationTypes
  })
  const wrapper = mount(QualificationTypeForm, {
    props: { initialData },
    global: { plugins: [PrimeVue], stubs: { MultiSelect: MultiSelectStub } },
  })
  return { wrapper, store }
}

beforeEach(() => vi.restoreAllMocks())

describe('qualification type form (E18)', () => {
  it('offers all other types but not the edited one', async () => {
    const { wrapper } = mountForm(type(2, 'Truppführer', [1]))
    await flushPromises()
    expect(wrapper.get('.ms').attributes('data-options')).toBe('Truppmann|Gruppenführer')
  })

  it('submits the chosen includes', async () => {
    const { wrapper, store } = mountForm()
    await flushPromises()
    const create = vi.spyOn(store, 'createQualificationType').mockResolvedValue(type(9, 'Neu'))
    await wrapper.get('#name').setValue('Neu')
    wrapper.getComponent(MultiSelectStub).vm.$emit('update:modelValue', [1])
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(create).toHaveBeenCalledWith(expect.objectContaining({ name: 'Neu', includes: [1] }))
  })

  it('shows the server validation error for a cycle', async () => {
    const { wrapper, store } = mountForm(type(1, 'Truppmann'))
    await flushPromises()
    vi.spyOn(store, 'updateQualificationType').mockRejectedValue({
      response: { data: { includes: ['Zyklische Zuordnung: Eine der gewählten Qualifikationen schließt diese bereits ein.'] } },
    })
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Zyklische Zuordnung')
  })
})
