import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DashboardView from '../DashboardView.vue'

const { auth, members, parents, qualifications, servicebook } = vi.hoisted(() => ({
  auth: { user: { first_name: 'Alex' }, canAccessModule: vi.fn((_perm: string) => true) },
  members: { fetchMembers: vi.fn(), pagination: { count: 48 } },
  parents: { fetchParents: vi.fn(), pagination: { count: 31 } },
  qualifications: { fetchStatistics: vi.fn(), statistics: { total_qualifications: 12, expiring_qualifications: 2 } },
  servicebook: { fetchChartData: vi.fn(), chartLoading: false, chartData: null },
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => ({ activeDepartment: { code: 'NORD' } }) }))
vi.mock('@/stores/members', () => ({ useMembersStore: () => members }))
vi.mock('@/stores/parents', () => ({ useParentsStore: () => parents }))
vi.mock('@/stores/qualifications', () => ({ useQualificationsStore: () => qualifications }))
vi.mock('@/stores/servicebook', () => ({ useServicebookStore: () => servicebook }))

function render() {
  return mount(DashboardView, { global: { stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } } })
}

describe('DashboardView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    auth.canAccessModule.mockImplementation(() => true)
    members.fetchMembers.mockResolvedValue([])
    parents.fetchParents.mockResolvedValue([])
    qualifications.fetchStatistics.mockResolvedValue(null)
    servicebook.fetchChartData.mockResolvedValue(null)
  })

  it('links every key figure to its module and shows no placeholders', async () => {
    const wrapper = render()
    await flushPromises()
    const tiles = wrapper.findAll('.kpi-tile')
    expect(tiles.map(t => t.attributes('href'))).toEqual(['/members', '/parents', '/qualifications'])
    expect(tiles[0]!.text()).toContain('48')
    expect(tiles[2]!.text()).toContain('2 laufen bald ab')
    expect(wrapper.text()).not.toContain('Inventar-')
    expect(wrapper.find('.kpi-tile__value').text()).not.toBe('-')
    expect(wrapper.text()).toContain('NORD')
  })

  it('only shows figures and loads data the user may see', async () => {
    auth.canAccessModule.mockImplementation((perm: string) => perm === 'view_member')
    const wrapper = render()
    await flushPromises()
    expect(wrapper.findAll('.kpi-tile').map(t => t.attributes('href'))).toEqual(['/members'])
    expect(parents.fetchParents).not.toHaveBeenCalled()
    expect(servicebook.fetchChartData).not.toHaveBeenCalled()
  })

  it('marks a failed source instead of showing a misleading zero and retries', async () => {
    parents.fetchParents.mockRejectedValueOnce(new Error('offline'))
    const wrapper = render()
    await flushPromises()
    const parentTile = wrapper.findAll('.kpi-tile')[1]!
    expect(parentTile.text()).toContain('Nicht geladen')
    expect(parentTile.find('.kpi-tile__value').text()).toBe('–')
    const notice = wrapper.get('.dashboard-notice')
    expect(notice.attributes('role')).toBe('alert')
    await notice.get('button').trigger('click')
    await flushPromises()
    expect(parents.fetchParents).toHaveBeenCalledTimes(2)
    expect(wrapper.find('.dashboard-notice').exists()).toBe(false)
  })
})
