import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import PortalStatusChip, { type PortalStatus } from '../PortalStatusChip.vue'

describe('PortalStatusChip', () => {
  const cases: [PortalStatus, string][] = [
    ['expected', 'Erwartet'], ['no-response', 'Keine Rückmeldung'], ['declined', 'Abgemeldet'],
    ['unavailable', 'Nicht möglich'], ['registered', 'Angemeldet'], ['waitlist', 'Warteliste'], ['assigned', 'Zugeteilt'],
    ['applied', 'Beworben'], ['not-selected', 'Nicht berücksichtigt'], ['session-cancelled', 'Abgesagt'],
  ]
  it.each(cases)('renders %s with icon and text', (status, label) => {
    const wrapper = mount(PortalStatusChip, { props: { status } })
    expect(wrapper.text()).toBe(label)
    expect(wrapper.find('i[aria-hidden="true"]').exists()).toBe(true)
  })
  it('uses a lock icon for unavailable', () => {
    expect(mount(PortalStatusChip, { props: { status: 'unavailable' } }).find('i').classes()).toContain('pi-lock')
  })
})
