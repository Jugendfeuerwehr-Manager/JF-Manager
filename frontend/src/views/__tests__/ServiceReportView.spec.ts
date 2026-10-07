import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { reactive } from 'vue'
import ServiceReportView from '../ServiceReportView.vue'
import { servicesApi } from '@/api/servicebook'
import type { AttendanceReport, AttendanceReportGroup } from '@/types/servicebook'

const route = reactive({ query: {} as Record<string, string> })
const replace = vi.fn((target: { query: Record<string, string> }) => { route.query = target.query })
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push: vi.fn(), replace }) }))
vi.mock('@/api/servicebook', () => ({ servicesApi: { getAttendanceReport: vi.fn() } }))

const months = [
  { month: '2026-09', present: 2, excused: 0, absent: 0, recorded: 2, rate: 100 },
  { month: '2026-10', present: 1, excused: 0, absent: 1, recorded: 2, rate: 50 },
]

function group(people: AttendanceReportGroup['people']): AttendanceReportGroup {
  return {
    summary: { present: 3, excused: 0, absent: 1, recorded: 4, rate: 75, people: people.length, with_warnings: people.filter((p) => p.warnings.length).length },
    months,
    people,
  }
}

const person = (id: number, full_name: string, warnings: AttendanceReportGroup['people'][number]['warnings'] = []) => ({
  id, full_name, present: 2, excused: 0, absent: 2, recorded: 4, rate: 50, hours: 4, months: [100, 0],
  trend: { previous: 100, recent: 0, delta: -100 }, missed_in_a_row: warnings.length ? 3 : 0, warnings,
})

const report: AttendanceReport = {
  period: { date_from: '2025-11-01', date_to: '2026-10-07' },
  services: { count: 2, hours: 4 },
  thresholds: { low_rate: 50, low_rate_min_records: 4, decline_points: 25, missed_in_a_row: 3 },
  members: group([person(1, 'Ada Aktiv'), person(2, 'Ben Bald', ['declining', 'missed_in_a_row'])]),
  staff: group([person(9, 'Alex Lehr')]),
}

function mountView() {
  return mount(ServiceReportView, { global: { directives: { tooltip: () => {} } } })
}

beforeEach(() => {
  route.query = {}
  replace.mockClear()
  vi.mocked(servicesApi.getAttendanceReport).mockReset().mockResolvedValue({ data: report } as never)
})

describe('attendance report view', () => {
  it('loads the last twelve months and shows tiles, months and people with warnings', async () => {
    const wrapper = mountView()
    await flushPromises()

    const params = vi.mocked(servicesApi.getAttendanceReport).mock.calls[0]![0]
    expect(params.date_from.endsWith('-01')).toBe(true)
    expect(wrapper.text()).toContain('Teilnahmequote')
    expect(wrapper.findAll('.month-chart__slot')).toHaveLength(2)
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    expect(wrapper.text()).toContain('Deutlicher Rückgang')
    expect(wrapper.text()).toContain('3× in Folge gefehlt')
  })

  it('switches group and filter in the URL without refetching', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[aria-label="Anzeigen"]').findAll('button')[1]!.trigger('click')
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    expect(replace).toHaveBeenLastCalledWith({ query: { show: 'warnings' } })

    await wrapper.get('[aria-label="Personengruppe"]').findAll('button')[1]!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Hinweise')
    expect(servicesApi.getAttendanceReport).toHaveBeenCalledTimes(1)
  })

  it('refetches for another period', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[aria-label="Zeitraum"]').findAll('button')[0]!.trigger('click')
    await flushPromises()
    expect(servicesApi.getAttendanceReport).toHaveBeenCalledTimes(2)
    expect(replace).toHaveBeenLastCalledWith({ query: { range: '3m' } })
  })

  it('explains a missing attendance right', async () => {
    vi.mocked(servicesApi.getAttendanceReport).mockRejectedValueOnce({ response: { status: 403, data: {} } })
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Keine Berechtigung')
    expect(wrapper.find('table').exists()).toBe(false)
  })
})
