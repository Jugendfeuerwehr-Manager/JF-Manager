import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import Tooltip from 'primevue/tooltip'
import ServiceListItem from '../molecules/ServiceListItem.vue'
import type { Service } from '@/types/servicebook'

const global = {
  plugins: [PrimeVue],
  directives: { tooltip: Tooltip },
  stubs: { RouterLink: { props: ['to'], template: '<a :data-to="JSON.stringify(to)"><slot /></a>' } },
}

describe('ServiceListItem', () => {
  const base: Service = {
    id: 3, start: '2026-10-06T18:00:00+02:00', end: '2026-10-06T20:00:00+02:00', place: 'Gerätehaus', topic: 'Knoten',
    operations_manager: [], attendance_summary: { present: 5, excused: 1, absent: 1, total: 7 }, has_events: false,
  }

  it('offers attendance for started services and summarises it in words', () => {
    const wrapper = mount(ServiceListItem, { props: { service: base }, global })
    expect(wrapper.find('[data-to*="service-attendance"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('5 anwesend · 1 entschuldigt · 1 fehlt')
  })

  it('only offers editing for future services', () => {
    const future = { ...base, start: '2099-01-01T18:00:00Z', end: '2099-01-01T20:00:00Z', attendance_summary: { present: 0, excused: 0, absent: 0, total: 0 } }
    const wrapper = mount(ServiceListItem, { props: { service: future }, global })
    expect(wrapper.find('[data-to*="service-attendance"]').exists()).toBe(false)
    expect(wrapper.find('[aria-label$="bearbeiten"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Anwesenheit offen')
  })

  it('opens the service editor from the row, also for services with an exercise', () => {
    const linked = { ...base, training_session: 9, training_status: 'published' } as Service
    const wrapper = mount(ServiceListItem, { props: { service: linked }, global })
    const title = wrapper.find('.service-row__title a')
    expect(JSON.parse(title.attributes('data-to')!)).toEqual({ name: 'service-edit', params: { id: 3 } })
    expect(wrapper.find('[aria-label="Übungsplan zu Knoten öffnen"]').exists()).toBe(true)
  })
})
