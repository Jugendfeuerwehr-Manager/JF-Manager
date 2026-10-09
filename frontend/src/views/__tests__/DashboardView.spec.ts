import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
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
const { inboxList } = vi.hoisted(() => ({ inboxList: vi.fn() }))
vi.mock('@/api/inbox', () => ({ inboxApi: { list: inboxList, counts: vi.fn().mockResolvedValue({ data: {} }), markRead: vi.fn().mockResolvedValue({ data: {} }) } }))
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
    setActivePinia(createPinia())
    vi.clearAllMocks()
    auth.canAccessModule.mockImplementation(() => true)
    summary.mockResolvedValue({ data: full })
    servicebook.fetchChartData.mockResolvedValue(null)
    inboxList.mockResolvedValue({ data: { count: 0, results: [] } })
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

  it('shows the three most urgent inbox tasks and hides the tile without any', async () => {
    const task = (id: number) => ({ id, title: `Aufgabe ${id}`, category: 'requests', department: 'Mitte', link: `/x/${id}` })
    inboxList.mockImplementation(async (filters: { type?: string }) => ({
      data: filters.type === 'task' ? { count: 4, results: [task(1), task(2), task(3), task(4)] } : { count: 0, results: [] },
    }))
    const wrapper = render()
    await flushPromises()
    expect(inboxList).toHaveBeenCalledWith({ type: 'task' })
    expect(inboxList).toHaveBeenCalledWith({ type: 'notice', unread: true })
    const tile = wrapper.get('[aria-labelledby="inbox-title"]')
    expect(tile.findAll('.task')).toHaveLength(3)
    expect(tile.get('a[href="/eingang"]').text()).toContain('Zum Eingang')
    inboxList.mockResolvedValue({ data: { count: 0, results: [] } })
    const empty = render()
    await flushPromises()
    expect(empty.find('[aria-labelledby="inbox-title"]').exists()).toBe(false)
  })

  it('shows unread notices even without open tasks, linking each entry', async () => {
    const notice = (id: number) => ({ id, title: `Hinweis ${id}`, category: 'registrations', department: 'Mitte', link: `/n/${id}`, type: 'notice', read: false })
    inboxList.mockImplementation(async (filters: { type?: string }) => ({
      data: filters.type === 'notice' ? { count: 4, results: [notice(1), notice(2), notice(3), notice(4)] } : { count: 0, results: [] },
    }))
    const wrapper = render()
    await flushPromises()
    const tile = wrapper.get('[aria-labelledby="inbox-title"]')
    expect(tile.text()).toContain('Neue Hinweise')
    const notices = tile.findAll('.task--notice')
    expect(notices).toHaveLength(3)
    expect(notices[0]!.get('a').attributes('href')).toBe('/n/1')
    expect(notices[0]!.text()).toContain('Neu')
    expect(tile.text()).not.toContain('Offene Aufgaben')
  })
})
