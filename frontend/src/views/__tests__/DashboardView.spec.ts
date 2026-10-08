import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DashboardView from '../DashboardView.vue'
import type { DashboardSummary } from '@/api/dashboard'

const { auth, servicebook, summary } = vi.hoisted(() => ({
  auth: { user: { first_name: 'Alex' }, canAccessModule: vi.fn((_perm: string) => true) },
  servicebook: { fetchChartData: vi.fn(), chartLoading: false, chartData: null },
  summary: vi.fn(),
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => ({ activeDepartment: { code: 'NORD' } }) }))
vi.mock('@/stores/servicebook', () => ({ useServicebookStore: () => servicebook }))
vi.mock('@/api/dashboard', () => ({ dashboardApi: { summary } }))

const today = new Date()
today.setHours(18, 0, 0, 0)
const full: DashboardSummary = {
  members: { total: 48 },
  parents: { total: 31 },
  qualifications: { expired: 1, expiring: { 30: 2, 60: 4, 90: 5 }, without_evidence: 3 },
  services: { upcoming_days: 14, upcoming: 2, next: { id: 7, start: today.toISOString(), topic: 'Stationsausbildung', place: 'Gerätehaus' } },
  orders: { open: 0 },
  lists: { open: 2 },
}

function render() {
  return mount(DashboardView, { global: { stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } } })
}

describe('DashboardView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    auth.canAccessModule.mockImplementation(() => true)
    summary.mockResolvedValue({ data: full })
    servicebook.fetchChartData.mockResolvedValue(null)
  })

  it('loads counts from one summary and links every key figure', async () => {
    const wrapper = render()
    await flushPromises()
    expect(summary).toHaveBeenCalledTimes(1)
    const tiles = wrapper.findAll('.kpi-tile')
    expect(tiles.map((t) => t.attributes('href'))).toEqual(['/members', '/qualifications', '/orders', '/lists'])
    expect(tiles[0]!.text()).toContain('48')
    expect(tiles[0]!.text()).toContain('31 Elternkontakte')
    expect(tiles[1]!.text()).toContain('1 abgelaufen')
    expect(wrapper.text()).toContain('NORD')
  })

  it('lists next tasks with one action each and skips empty ones', async () => {
    const wrapper = render()
    await flushPromises()
    const tasks = wrapper.findAll('.task')
    expect(tasks.map((t) => t.get('.task__action').attributes('href'))).toEqual([
      '/servicebook/7/attendance', '/qualifications?view=expired', '/qualifications', '/qualifications?view=missing', '/lists',
    ])
    expect(tasks[0]!.text()).toContain('Heute: Stationsausbildung')
    expect(wrapper.get('.task-list').text()).not.toContain('Bestellung')
  })

  it('hides figures of modules without access', async () => {
    auth.canAccessModule.mockImplementation((perm: string) => perm === 'view_member')
    summary.mockResolvedValue({ data: { ...full, qualifications: null, orders: null, lists: null, services: null } })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.findAll('.kpi-tile').map((t) => t.attributes('href'))).toEqual(['/members'])
    expect(servicebook.fetchChartData).not.toHaveBeenCalled()
  })

  it('marks a failed summary instead of showing misleading zeros and retries', async () => {
    summary.mockRejectedValueOnce(new Error('offline'))
    const wrapper = render()
    await flushPromises()
    const tile = wrapper.findAll('.kpi-tile')[0]!
    expect(tile.text()).toContain('Nicht geladen')
    expect(tile.find('.kpi-tile__value').text()).toBe('–')
    await wrapper.get('.dashboard-notice button').trigger('click')
    await flushPromises()
    expect(summary).toHaveBeenCalledTimes(2)
    expect(wrapper.find('.dashboard-notice').exists()).toBe(false)
    expect(wrapper.findAll('.task')).toHaveLength(5)
  })
})
