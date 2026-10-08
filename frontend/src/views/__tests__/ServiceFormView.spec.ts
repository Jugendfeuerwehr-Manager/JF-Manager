import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ServiceFormView from '../ServiceFormView.vue'

const { store, route, replace } = vi.hoisted(() => ({
  store: {
    currentService: { id: 11, start: '2026-10-06T18:00:00+02:00', end: '2026-10-06T20:00:00+02:00', topic: 'Stationsausbildung', place: 'Gerätehaus' },
    fetchService: vi.fn(),
    updateService: vi.fn(),
    createService: vi.fn(),
  },
  route: { params: { id: '11' } as Record<string, string>, query: {} as Record<string, string> },
  replace: vi.fn(),
}))
vi.mock('@/stores/servicebook', () => ({ useServicebookStore: () => store }))
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push: vi.fn(), replace }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))

function render() {
  return mount(ServiceFormView, {
    global: {
      stubs: {
        RouterLink: { props: ['to'], template: '<a><slot /></a>' },
        ServiceForm: { props: ['submitLabel'], template: '<div class="form-stub">{{ submitLabel }}</div>' },
        AttendanceManager: { template: '<div class="attendance-stub" />' },
      },
    },
  })
}

describe('ServiceFormView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    route.params = { id: '11' }
    route.query = {}
  })

  it('shows the service as heading and switches to attendance as a tab', async () => {
    const wrapper = render()
    await flushPromises()
    expect(wrapper.get('h1').text()).toBe('Stationsausbildung')
    const tabs = wrapper.findAll('[role="tab"]')
    expect(tabs.map(t => t.attributes('aria-selected'))).toEqual(['true', 'false'])
    expect(wrapper.get('#panel-attendance').isVisible()).toBe(false)
    await tabs[1]!.trigger('click')
    expect(tabs[1]!.attributes('aria-selected')).toBe('true')
    expect(replace).toHaveBeenCalledWith({ query: { tab: 'attendance' } })
    await wrapper.get('[role="tablist"]').trigger('keydown', { key: 'ArrowLeft' })
    expect(tabs[0]!.attributes('aria-selected')).toBe('true')
  })

  it('opens attendance directly from the link and offers no tabs when creating', async () => {
    route.query = { tab: 'attendance' }
    const editing = render()
    await flushPromises()
    expect(editing.findAll('[role="tab"]')[1]!.attributes('aria-selected')).toBe('true')

    route.params = {}
    route.query = {}
    const creating = render()
    await flushPromises()
    expect(creating.find('[role="tablist"]').exists()).toBe(false)
    expect(creating.get('h1').text()).toBe('Neuer Dienst')
    expect(creating.get('.form-stub').text()).toBe('Dienst anlegen')
  })
})
