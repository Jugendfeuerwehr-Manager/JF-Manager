import { afterEach, describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import PortalCancelSheet from '../PortalCancelSheet.vue'
import { makeItem } from '@/utils/__tests__/portalFixtures'

const mia = { id: 2, relation: 'child' as const, first_name: 'Mia', last_name: 'B' }
let wrapper: VueWrapper | null = null
const render = (props: Record<string, unknown> = {}) => {
  wrapper = mount(PortalCancelSheet, { props: { item: makeItem({ state: 'registered' }), person: mia, ...props }, global: { plugins: [PrimeVue] }, attachTo: document.body })
  return wrapper
}
afterEach(() => { wrapper?.unmount(); wrapper = null })

describe('PortalCancelSheet', () => {
  it('is a labelled modal dialog titled with the name and takes focus', async () => {
    const w = render()
    const dialog = w.get('[role="dialog"]')
    expect(dialog.attributes('aria-modal')).toBe('true')
    const title = w.get(`#${dialog.attributes('aria-labelledby')}`)
    expect(title.text()).toBe('Mia abmelden')
    await w.vm.$nextTick()
    expect(document.activeElement).toBe(title.element)
    expect(w.text()).toContain('Orientierungsmarsch')
  })

  it('offers the five reasons as radios and submits the chosen one with the trimmed note', async () => {
    const w = render()
    const radios = w.findAll('input[type="radio"]')
    expect(radios.map(r => r.attributes('value'))).toEqual(['krankheit', 'schule_beruf', 'urlaub', 'familie', 'sonstiges'])
    await radios[2]!.setValue(true)
    await w.get('textarea').setValue('  Ab Freitag verreist  ')
    await w.findAll('button').find(b => b.text() === 'Abmeldung senden')!.trigger('click')
    expect(w.emitted('submit')![0]).toEqual([{ reason_category: 'urlaub', reason_note: 'Ab Freitag verreist' }])
  })

  it('allows sending without a reason (optional in the backend)', async () => {
    const w = render()
    await w.findAll('button').find(b => b.text() === 'Abmeldung senden')!.trigger('click')
    expect(w.emitted('submit')![0]).toEqual([{ reason_category: '', reason_note: '' }])
  })

  it('counts note characters and limits to 200', async () => {
    const w = render()
    expect(w.text()).toContain('Bitte keine Gesundheitsdetails angeben. 0/200 Zeichen')
    await w.get('textarea').setValue('abc')
    expect(w.text()).toContain('3/200 Zeichen')
    expect(w.get('textarea').attributes('maxlength')).toBe('200')
  })

  it('explains the waitlist promotion for limited services', () => {
    expect(render().text()).toContain('Mias Platz wird frei und die nächste Person auf der Warteliste rückt nach')
  })

  it('addresses the own account directly and omits waitlist text without a limit', () => {
    const w = render({ person: { id: 1, relation: 'self', first_name: 'Anna', last_name: 'B' }, item: makeItem({ limited: false, free_places: null }) })
    expect(w.get('h2').text()).toBe('Abmelden')
    expect(w.text()).not.toContain('Warteliste')
  })

  it('closes on Escape and Abbrechen, and shows errors', async () => {
    const w = render({ error: 'Fehler beim Speichern' })
    expect(w.get('[role="alert"]').text()).toBe('Fehler beim Speichern')
    await w.get('[role="dialog"]').trigger('keydown', { key: 'Escape' })
    await w.findAll('button').find(b => b.text() === 'Abbrechen')!.trigger('click')
    expect(w.emitted('close')).toHaveLength(2)
  })
})
