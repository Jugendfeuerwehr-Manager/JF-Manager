import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ServiceMobileList from '../organisms/ServiceMobileList.vue'

const { servicesApi } = vi.hoisted(() => ({ servicesApi: { getOverview: vi.fn() } }))
vi.mock('@/api/servicebook', () => ({ servicesApi }))

const RouterLink = { props: ['to'], template: '<a :data-to="JSON.stringify(to)"><slot /></a>' }
const card = (id: number, topic: string, counts = { expected: 11, cancelled: 3, recorded: 0, total: 14 }) => ({
  id, date: '2026-10-14', start: '2026-10-14T18:00:00', end: '2026-10-14T20:00:00', topic,
  groups: ['Gruppe 2'], session_id: 4, mode: 'opt_out', counts,
})

describe('ServiceMobileList', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    servicesApi.getOverview.mockResolvedValue({
      data: {
        today: [card(1, 'Knoten und Stiche')],
        open: [card(2, 'Fahrzeugkunde HLF', { expected: 10, cancelled: 1, recorded: 6, total: 10 })],
        upcoming: [card(3, 'Orientierungsmarsch')],
      },
    })
  })

  it('renders the three buckets with counters and the primary action on today', async () => {
    const wrapper = mount(ServiceMobileList, { props: { department: 7 }, global: { plugins: [PrimeVue], stubs: { RouterLink } } })
    await flushPromises()
    expect(servicesApi.getOverview).toHaveBeenCalledWith({ department: 7 })
    expect(wrapper.findAll('h2').map((h) => h.text())).toEqual(['Heute', 'Anwesenheit offen', 'Demnächst'])
    const today = wrapper.findAll('article')[0]!
    expect(today.text()).toContain('Knoten und Stiche')
    expect(today.text()).toContain('Gruppe 2')
    expect(today.get('dl').attributes('aria-label')).toBe('Zähler: 11 erwartet, 3 abgemeldet, 0 erfasst')
    expect(today.get('.card-action--primary').text()).toBe('Anwesenheit erfassen')
    expect(wrapper.findAll('article')[1]!.text()).toContain('4 offen')
  })

  it('shows an empty state without services', async () => {
    servicesApi.getOverview.mockResolvedValue({ data: { today: [], open: [], upcoming: [] } })
    const wrapper = mount(ServiceMobileList, { global: { plugins: [PrimeVue], stubs: { RouterLink } } })
    await flushPromises()
    expect(wrapper.text()).toContain('Keine Dienste')
  })
})
