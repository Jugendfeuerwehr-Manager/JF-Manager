import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import MembershipTimeline from '../MembershipTimeline.vue'
import { membershipApi } from '@/api/membership'
import type { MembershipEvent } from '@/types/membership'

vi.mock('@/api/membership', () => ({ membershipApi: { listEvents: vi.fn(), correctEvent: vi.fn() } }))

const event = (extra: Partial<MembershipEvent> = {}): MembershipEvent => ({
  id: 1, member: 7, department: 2, department_name: 'Mitte', date: '2026-05-01', kind: 'exit_other',
  kind_label: 'Abgang sonstige', exit_reason: '', exit_reason_label: '', from_status_name: 'Aktiv',
  to_status_name: 'Ausgetreten', note: '', created_by_name: null, created_at: '2026-05-01T10:00:00Z', ...extra,
})

describe('MembershipTimeline', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads the movements of the member and shows them', async () => {
    vi.mocked(membershipApi.listEvents).mockResolvedValue({ data: { count: 1, results: [event()] } } as never)
    const wrapper = mount(MembershipTimeline, { props: { memberId: 7 } })
    await flushPromises()
    expect(membershipApi.listEvents).toHaveBeenCalledWith({ member: 7, limit: 200 })
    expect(wrapper.text()).toContain('Abgang sonstige')
    expect(wrapper.text()).toContain('Aktiv → Ausgetreten')
  })

  it('lets editors complete a missing exit reason', async () => {
    vi.mocked(membershipApi.listEvents).mockResolvedValue({ data: { count: 1, results: [event()] } } as never)
    vi.mocked(membershipApi.correctEvent).mockResolvedValue({
      data: event({ exit_reason: 'school', exit_reason_label: 'Belastung durch Schule' }),
    } as never)
    const wrapper = mount(MembershipTimeline, { props: { memberId: 7, canEdit: true } })
    await flushPromises()
    await wrapper.find('select').setValue('school')
    await flushPromises()
    expect(membershipApi.correctEvent).toHaveBeenCalledWith(1, { exit_reason: 'school' })
    expect(wrapper.text()).toContain('Grund: Belastung durch Schule')
    expect(wrapper.find('select').exists()).toBe(false)
  })

  it('readers see the hint but no editor', async () => {
    vi.mocked(membershipApi.listEvents).mockResolvedValue({ data: { count: 1, results: [event()] } } as never)
    const wrapper = mount(MembershipTimeline, { props: { memberId: 7 } })
    await flushPromises()
    expect(wrapper.text()).toContain('Grund fehlt')
    expect(wrapper.find('select').exists()).toBe(false)
  })
})
