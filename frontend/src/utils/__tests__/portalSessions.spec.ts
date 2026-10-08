import { describe, expect, it } from 'vitest'
import type { PortalPerson } from '@/api/portal'
import { makeItem } from './portalFixtures'
import { describeSession, formatDay, placesText, statusBanner } from '../portalSessions'

const mia: PortalPerson = { id: 2, relation: 'child', first_name: 'Mia', last_name: 'B' }
const me: PortalPerson = { id: 1, relation: 'self', first_name: 'Anna', last_name: 'B' }

describe('describeSession', () => {
  it('offers "Mia anmelden" for opt-in without response and "Anmelden" for the own account', () => {
    expect(describeSession(makeItem(), mia).action).toMatchObject({ label: 'Mia anmelden', target: 'registered', opensSheet: false, kind: 'register' })
    expect(describeSession(makeItem(), me).action?.label).toBe('Anmelden')
    expect(describeSession(makeItem(), mia).chip).toBe('no-response')
  })

  it('offers the waitlist wording when no place is free', () => {
    const view = describeSession(makeItem({ free_places: 0 }), mia)
    expect(view.action?.label).toBe('Mia auf die Warteliste setzen')
    expect(view.hint).toContain('Warteliste')
  })

  it('opens the sheet for cancelling an expected person in opt-out mode', () => {
    const view = describeSession(makeItem({ mode: 'opt_out', state: 'expected', limited: false, free_places: null, may_register: false, may_cancel: true }), mia)
    expect(view.chip).toBe('expected')
    expect(view.action).toMatchObject({ label: 'Mia abmelden', target: 'cancelled', opensSheet: true })
  })

  it('shows a registered opt-out row (after taking a cancellation back) as expected', () => {
    const view = describeSession(makeItem({ mode: 'opt_out', state: 'registered', may_cancel: true, may_register: false }), me)
    expect(view.chip).toBe('expected')
    expect(view.action?.label).toBe('Abmelden')
  })

  it('offers to take a cancellation back in opt-out and shows the reason', () => {
    const view = describeSession(makeItem({ mode: 'opt_out', state: 'cancelled', reason_category: 'urlaub', may_register: true }), mia)
    expect(view.chip).toBe('declined')
    expect(view.action).toMatchObject({ label: 'Abmeldung zurücknehmen', target: 'registered', opensSheet: false })
    expect(view.hint).toBe('Grund: Urlaub')
  })

  it('maps the waitlist: position and leave action without sheet', () => {
    const view = describeSession(makeItem({ state: 'waitlisted', waitlist_position: 2, may_cancel: true, may_register: false }), mia)
    expect(view.chip).toBe('waitlist')
    expect(view.hint).toBe('Warteliste, Platz 2')
    expect(view.action).toMatchObject({ label: 'Von der Warteliste abmelden', target: 'cancelled', opensSheet: false })
  })

  it('maps assignment mode: apply, withdraw, assigned, not selected', () => {
    const base = { mode: 'assignment' as const }
    expect(describeSession(makeItem(base), mia).action).toMatchObject({ label: 'Mia bewerben', target: 'applied' })
    const applied = describeSession(makeItem({ ...base, state: 'applied', may_cancel: true, may_register: false }), mia)
    expect(applied.chip).toBe('applied')
    expect(applied.action).toMatchObject({ label: 'Bewerbung zurückziehen', target: 'withdrawn' })
    const assigned = describeSession(makeItem({ ...base, state: 'assigned', may_cancel: true, may_register: false }), mia)
    expect(assigned.chip).toBe('assigned')
    expect(assigned.action?.opensSheet).toBe(true)
    const none = describeSession(makeItem({ ...base, state: 'not_selected', may_register: false }), mia)
    expect(none.chip).toBe('not-selected')
    expect(none.action).toBeNull()
  })

  it('explains a missed cancellation deadline and disables the action', () => {
    const view = describeSession(makeItem({
      state: 'registered', may_cancel: false, may_register: false,
      cancel_blocked: { code: 'deadline_passed', detail: 'x', reasons: [] },
    }), mia)
    expect(view.enabled).toBe(false)
    expect(view.action?.label).toBe('Mia abmelden')
    expect(view.blocked).toBe('Abmeldung nur noch direkt bei der Dienstleitung.')
  })

  it('explains a missed registration deadline with the server text', () => {
    const view = describeSession(makeItem({ register_blocked: { code: 'deadline_passed', detail: 'Anmeldeschluss war am Do 16.10.', reasons: [] }, may_register: false }), mia)
    expect(view.enabled).toBe(false)
    expect(view.blocked).toBe('Anmeldeschluss war am Do 16.10.')
  })

  it('shows "Nicht möglich" with the reasons and no action when not eligible', () => {
    const view = describeSession(makeItem({ may_register: false, eligibility: { ok: false, reasons: ['Alter: mindestens 15'], audience_notice: null }, register_blocked: { code: 'not_eligible', detail: 'x', reasons: [] } }), mia)
    expect(view.chip).toBe('unavailable')
    expect(view.action).toBeNull()
    expect(view.unavailableReasons).toEqual(['Alter: mindestens 15'])
  })

  it('has no action for cancelled sessions', () => {
    const view = describeSession(makeItem({ session_status: 'cancelled', state: 'registered', may_cancel: true }), mia)
    expect(view.chip).toBe('session-cancelled')
    expect(view.action).toBeNull()
  })
})

describe('formatting', () => {
  it('formats days, places and banner', () => {
    expect(formatDay('2026-10-14')).toBe('Mi 14.10.')
    expect(placesText(makeItem())).toEqual({ text: 'Noch 3 Plätze frei', ratio: null })
    expect(placesText(makeItem({ max_participants: 20, free_places: 3 }))).toEqual({ text: 'Noch 3 von 20 Plätzen frei', ratio: 0.85 })
    expect(placesText(makeItem({ mode: 'opt_out', limited: false, free_places: null }))).toBeNull()
    expect(statusBanner(makeItem({ state: 'registered' }), mia).text).toBe('Mia ist angemeldet')
    expect(statusBanner(makeItem({ state: 'registered' }), me).text).toBe('Du bist angemeldet')
  })
})
