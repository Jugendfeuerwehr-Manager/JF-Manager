import { afterEach, describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import PortalPositionSheet from '../PortalPositionSheet.vue'
import { makeItem } from '@/utils/__tests__/portalFixtures'
import { describeSession, positionLines } from '@/utils/portalSessions'

const mia = { id: 2, relation: 'child' as const, first_name: 'Mia', last_name: 'B' }
const positions = [
  { id: 1, label: 'Wachführung', max: 1, free: 1, suits: false },
  { id: 2, label: 'Trupp', max: 2, free: 0, suits: true },
  { id: 3, label: 'Melder', max: 1, free: 1, suits: true },
]
let wrapper: VueWrapper | null = null
const render = (over: Record<string, unknown> = {}) => {
  wrapper = mount(PortalPositionSheet, { props: { item: makeItem({ positions, ...over }), person: mia }, global: { plugins: [PrimeVue] }, attachTo: document.body })
  return wrapper
}
afterEach(() => { wrapper?.unmount(); wrapper = null })
const button = (w: VueWrapper, label: string) => w.findAll('button').find(b => b.text() === label)!

describe('PortalPositionSheet', () => {
  it('defaults to "beliebig", locks unsuitable positions and shows free places without names', async () => {
    const w = render()
    expect(w.get('[role="dialog"]').text()).toContain('Mia anmelden')
    const radios = w.findAll('input[type="radio"]')
    expect(radios.map(r => r.attributes('value'))).toEqual(['any', '1', '2', '3'])
    expect((radios[0]!.element as HTMLInputElement).checked).toBe(true)
    expect(radios[1]!.attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('Voraussetzung nicht erfüllt')
    expect(w.text()).toContain('Voll – Warteliste')
    await button(w, 'Anmelden').trigger('click')
    expect(w.emitted('submit')![0]).toEqual([null])
  })

  it('announces the waiting list for a full position and sends the chosen id', async () => {
    const w = render()
    await w.findAll('input[type="radio"]')[2]!.setValue(true)
    expect(w.text()).toContain('kommt auf die Warteliste')
    await button(w, 'Auf die Warteliste').trigger('click')
    expect(w.emitted('submit')![0]).toEqual([2])
  })

  it('asks for an optional wish in assignment mode (Q3)', async () => {
    const w = render({ mode: 'assignment', state: 'no_response' })
    expect(w.text()).toContain('Wunschposition')
    expect(w.text()).toContain('Mia bewerben')
    await button(w, 'Bewerbung senden').trigger('click')
    expect(w.emitted('submit')![0]).toEqual([null])
  })
})

describe('portal position texts', () => {
  it('lists free places per position and the held position', () => {
    expect(positionLines(makeItem({ positions })).map(p => p.text)).toEqual(['1 von 1 frei', 'voll', '1 von 1 frei'])
    expect(describeSession(makeItem({ positions, state: 'registered', slot_label: 'Melder' }), mia).hint).toBe('Angemeldet als Melder')
    expect(describeSession(makeItem({ positions, state: 'waitlisted', waitlist_position: 2, preferred_label: 'Trupp' }), mia).hint).toBe('Warteliste, Platz 2 (Trupp)')
  })
})
