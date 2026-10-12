import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import MobileTrainingPlanner from '../MobileTrainingPlanner.vue'

const mocks = vi.hoisted(() => ({ plan: vi.fn(), news: vi.fn(), confirm: vi.fn(), deleteSession: vi.fn(), push: vi.fn() }))
vi.mock('@/api/training', () => ({ trainingSessionsApi: { plan: mocks.plan } }))
vi.mock('@/api/participation', () => ({ participationApi: { newResponses: mocks.news } }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: mocks.push }) }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: mocks.confirm }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))
vi.mock('@/stores/training', () => ({ useTrainingStore: () => ({ deleteSession: mocks.deleteSession }) }))

const Button = { props: ['label', 'ariaLabel'], emits: ['click'], template: '<button type="button" :aria-label="ariaLabel" @click="$emit(\'click\')">{{ label }}</button>' }

function mount() {
  return shallowMount(MobileTrainingPlanner, { props: { sessionId: 4 }, global: { stubs: { Button, RouterLink: true } } })
}

describe('MobileTrainingPlanner registrations (NOTIF-02)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
    mocks.plan.mockResolvedValue({ data: {
      id: 4, revision: 1, title: 'Zeltlager', date: '2030-01-01', start_time: '18:00:00', end_time: '20:00:00', status: 'published',
      description: '', location: '', notes: '', department: 1, groups: [], recurrence_rule: null, can_manage_plan: true, blocks: [],
      linked_service_id: null, linked_service_start: null, requires_service_confirmation: false,
    } })
  })

  it('shows new responses on the button and opens the registrations', async () => {
    mocks.news.mockResolvedValue({ data: { sessions: { 4: 2 } } })
    const wrapper = mount()
    await flushPromises()
    expect(mocks.news).toHaveBeenCalledWith([4])
    const button = wrapper.get('button[aria-label="Meldungen, 2 neue Rückmeldungen"]')
    expect(button.text()).toBe('Meldungen · 2 neu')
    await button.trigger('click')
    const dialog = wrapper.findComponent({ name: 'ParticipationDialog' })
    expect(dialog.props('visible')).toBe(true)
    expect(dialog.props('initialTab')).toBe('registrations')
  })

  it('shows a plain button without news', async () => {
    mocks.news.mockResolvedValue({ data: { sessions: {} } })
    const wrapper = mount()
    await flushPromises()
    expect(wrapper.get('button[aria-label="Meldungen"]').text()).toBe('Meldungen')
  })

  it('deletes the exercise from the phone view after confirmation', async () => {
    mocks.news.mockResolvedValue({ data: { sessions: {} } })
    mocks.deleteSession.mockResolvedValue(undefined)
    const wrapper = mount()
    await flushPromises()
    await wrapper.get('button[aria-label="Zeltlager löschen"]').trigger('click')
    const request = mocks.confirm.mock.calls[0]![0]
    expect(request.header).toBe('„Zeltlager“ löschen?')
    request.accept()
    await flushPromises()
    expect(mocks.deleteSession).toHaveBeenCalledWith(4, { deleteLinkedService: false })
    expect(mocks.push).toHaveBeenCalledWith('/training')
  })
})
