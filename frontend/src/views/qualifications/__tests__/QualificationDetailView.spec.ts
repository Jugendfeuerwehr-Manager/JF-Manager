import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import QualificationDetailView from '../QualificationDetailView.vue'
import { useQualificationsStore } from '@/stores/qualifications'
import type { Qualification } from '@/types/qualifications'

const push = vi.fn()
const route = { params: { id: '2' } }
const list = vi.fn()
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push }) }))
vi.mock('@/api/qualifications', () => ({ qualificationsApi: { list: (...args: unknown[]) => list(...args) } }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: vi.fn() }) }))

const record = (id: number, acquired: string, expires: string | null): Qualification => ({
  id, type: 5, type_name: 'Erste Hilfe', user: null, user_name: null, member: 9, member_name: 'Mia Beispiel',
  person_name: 'Mia Beispiel', date_acquired: acquired, date_expires: expires, issued_by: 'Kreis', note: '',
  is_expired: false, expires_soon: false, status_class: '', attachments: [],
})

function mountView(current: Qualification, history: Qualification[]) {
  setActivePinia(createPinia())
  const store = useQualificationsStore()
  vi.spyOn(store, 'fetchQualification').mockImplementation(async () => { store.currentQualification = current; return current })
  list.mockResolvedValue({ data: { results: history } })
  return mount(QualificationDetailView, { global: { stubs: { AttachmentsSection: true, RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } } })
}

beforeEach(() => { push.mockClear(); list.mockReset() })

describe('qualification detail', () => {
  it('offers renewal as the main action and lists the history of this person and type', async () => {
    const current = record(2, '2024-05-01', '2027-05-01')
    const wrapper = mountView(current, [current, record(1, '2022-05-01', '2024-05-01')])
    await flushPromises()
    expect(list).toHaveBeenCalledWith({ type: 5, member: 9, ordering: '-date_acquired', page_size: 50 })
    const items = wrapper.findAll('.history li')
    expect(items).toHaveLength(2)
    expect(items[0]!.attributes('aria-current')).toBe('true')
    expect(items[1]!.text()).toContain('Verlängert')
    await wrapper.findAll('button').find((b) => b.text().includes('Verlängern'))!.trigger('click')
    expect(push).toHaveBeenCalledWith({ path: '/qualifications/create', query: { renew: '2' } })
  })

  it('points from a renewed record to the current one instead of offering another renewal', async () => {
    const old = record(1, '2022-05-01', '2024-05-01')
    const wrapper = mountView(old, [record(2, '2024-05-01', '2027-05-01'), old])
    await flushPromises()
    expect(wrapper.get('[role="status"]').text()).toContain('Verlängert am 01.05.2024')
    expect(wrapper.get('[role="status"] a').attributes('href')).toBe('/qualifications/2')
    expect(wrapper.findAll('button').some((b) => b.text().includes('Verlängern'))).toBe(false)
  })
})
