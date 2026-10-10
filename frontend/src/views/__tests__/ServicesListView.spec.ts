import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import ServicesListView from '../ServicesListView.vue'

const { store, route, replace } = vi.hoisted(() => ({
  store: { services: [], servicesLoading: false, servicesError: null, servicesTotalCount: 30, fetchServices: vi.fn() },
  route: { query: {} as Record<string, string> }, replace: vi.fn(),
}))
vi.mock('@/stores/servicebook', () => ({ useServicebookStore: () => store }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ hasPerm: () => true }) }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => ({ activeDepartmentId: 7 }) }))
vi.mock('@/composables/useMobile', () => ({ useMobile: () => ({ isMobile: ref(true) }) }))
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push: vi.fn(), replace }) }))
vi.mock('@/api/servicebook', () => ({ servicesApi: { list: vi.fn() } }))
function render() {
  return mount(ServicesListView, { global: { stubs: {
    OverviewHeader: { template: '<header><slot name="actions" /></header>' },
    ServiceMobileList: { template: '<div class="mobile-overview" />' },
    ServicesList: { name: 'ServicesList', props: ['emptyTitle'], emits: ['page-change'], template: '<div class="past-list">{{ emptyTitle }}</div>' },
    ServiceFilters: true,
  } } })
}
describe('mobile service history', () => {
  beforeEach(() => { vi.clearAllMocks(); route.query = {} })
  it('switches to past services, paginates and returns to the overview', async () => {
    const wrapper = render(); await flushPromises()
    expect(wrapper.find('.mobile-overview').exists()).toBe(true)
    await wrapper.findAll('button').find(b => b.text() === 'Vergangen')!.trigger('click'); await flushPromises()
    expect(wrapper.get('.past-list').text()).toContain('Keine vergangenen Dienste')
    expect(store.fetchServices).toHaveBeenLastCalledWith(expect.objectContaining({ end__lte: expect.any(String), ordering: '-start', offset: 0, limit: 12 }))
    wrapper.findComponent({ name: 'ServicesList' }).vm.$emit('page-change', 2, 12)
    await flushPromises()
    expect(store.fetchServices).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 12 }))
    await wrapper.findAll('button').find(b => b.text() === 'Kommend')!.trigger('click')
    expect(wrapper.find('.mobile-overview').exists()).toBe(true)
    expect(replace).toHaveBeenLastCalledWith({ query: {} })
  })
  it('restores past scope and page from the URL on mobile', async () => {
    route.query = { scope: 'past', page: '2' }
    const wrapper = render(); await flushPromises()
    expect(wrapper.find('.past-list').exists()).toBe(true)
    expect(store.fetchServices).toHaveBeenCalledWith(expect.objectContaining({ offset: 12, ordering: '-start' }))
  })
})
