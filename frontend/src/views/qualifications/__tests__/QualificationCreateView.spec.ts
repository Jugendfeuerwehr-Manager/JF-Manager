import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, h } from 'vue'
import QualificationCreateView from '../QualificationCreateView.vue'
import { useQualificationsStore } from '@/stores/qualifications'

vi.mock('vue-router', () => ({ useRoute: () => ({ query: { renew: '4' } }), useRouter: () => ({ push: vi.fn() }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))

const FormStub = defineComponent({ name: 'QualificationForm', props: ['renewFrom'], setup: () => () => h('form') })

describe('renewing a qualification', () => {
  it('pre-fills the form from the record being renewed', async () => {
    setActivePinia(createPinia())
    const store = useQualificationsStore()
    const source = { id: 4, type_name: 'Sprechfunk', person_name: 'Jonas Muster', date_expires: '2026-10-28' }
    vi.spyOn(store, 'fetchQualificationTypes').mockResolvedValue([] as never)
    vi.spyOn(store, 'fetchQualification').mockResolvedValue(source as never)
    const wrapper = mount(QualificationCreateView, { global: { stubs: { QualificationForm: FormStub } } })
    await flushPromises()
    expect(wrapper.get('h1').text()).toBe('Qualifikation verlängern')
    expect(wrapper.text()).toContain('bisher gültig bis 28.10.2026')
    expect(wrapper.findComponent(FormStub).props('renewFrom')).toEqual(source)
  })
})
