import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, h, reactive } from 'vue'
import QualificationsDashboardView from '../QualificationsDashboardView.vue'
import { useQualificationsStore } from '@/stores/qualifications'

const route = reactive({ query: {} as Record<string, string> })
const replace = vi.fn((target: { query: Record<string, string> }) => { route.query = target.query })
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push: vi.fn(), replace }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: vi.fn() }) }))

const TableStub = defineComponent({ name: 'QualificationsTable', props: ['query'], setup: (_, { expose }) => { expose({ reload: vi.fn() }); return () => h('div') } })

function mountView() {
  return mount(QualificationsDashboardView, {
    global: {
      directives: { tooltip: () => {} },
      stubs: { QualificationsTable: TableStub, SpecialTasksTable: true, QualificationsMobileList: true, SpecialTasksMobileList: true, Menu: true, Tabs: true, TabList: true, Tab: true },
    },
  })
}

beforeEach(() => {
  route.query = {}
  replace.mockClear()
  setActivePinia(createPinia())
  const store = useQualificationsStore()
  vi.spyOn(store, 'fetchStatistics').mockImplementation(async () => {
    store.statistics = {
      total_qualifications: 12, expired_qualifications: 2, expiring_qualifications: 3,
      expiring_by_window: { 30: 3, 60: 5, 90: 7 }, without_evidence: 4,
      active_special_tasks: 1, completed_special_tasks: 0, recent_qualifications: [],
      expiring_qualifications_list: [], active_special_tasks_list: [],
    }
    return store.statistics
  })
})

describe('qualifications overview', () => {
  it('opens on current qualifications expiring within 30 days with counts per view', async () => {
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.findComponent(TableStub).props('query')).toEqual({ current: true, expiring_within: 30 })
    const views = wrapper.get('[aria-label="Ansicht"]').findAll('button').map((b) => b.text())
    expect(views).toEqual(['Läuft ab3', 'Abgelaufen2', 'Ohne Nachweis4', 'Alle12'])
    expect(wrapper.findAll('.p-button').filter((b) => b.text() === 'Neue Qualifikation')).toHaveLength(1)
  })

  it('keeps view and window in the URL and passes them to the list', async () => {
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[aria-label="Zeitraum"]').findAll('button')[2]!.trigger('click')
    expect(replace).toHaveBeenLastCalledWith({ query: { within: '90' } })
    await flushPromises()
    expect(wrapper.findComponent(TableStub).props('query')).toEqual({ current: true, expiring_within: 90 })
    expect(wrapper.get('[aria-label="Ansicht"]').findAll('button')[0]!.text()).toBe('Läuft ab7')

    await wrapper.get('[aria-label="Ansicht"]').findAll('button')[2]!.trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(TableStub).props('query')).toEqual({ current: true, without_evidence: true })
    expect(wrapper.find('[aria-label="Zeitraum"]').exists()).toBe(false)
  })

  it('shows a retryable error when the counts fail but keeps the list', async () => {
    const store = useQualificationsStore()
    vi.mocked(store.fetchStatistics).mockRejectedValueOnce(new Error('offline'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Übersicht konnte nicht geladen werden')
    expect(wrapper.findComponent(TableStub).exists()).toBe(true)
  })
})
