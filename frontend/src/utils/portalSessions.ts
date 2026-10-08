import type { PortalPerson, PortalReason, PortalSessionItem, PortalTarget } from '@/api/portal'
import type { PortalStatus } from '@/components/portal/PortalStatusChip.vue'

export const REASONS: { value: PortalReason, label: string }[] = [
  { value: 'krankheit', label: 'Krankheit' },
  { value: 'schule_beruf', label: 'Schule' },
  { value: 'urlaub', label: 'Urlaub' },
  { value: 'familie', label: 'Familie' },
  { value: 'sonstiges', label: 'Sonstiges' },
]
export const NOTE_MAX = 200

export function reasonLabel(value: string): string {
  return REASONS.find(r => r.value === value)?.label ?? ''
}

export type ActionKind = 'register' | 'apply' | 'cancel' | 'withdraw' | 'leave_waitlist' | 'undo_cancel'

export interface SessionAction {
  kind: ActionKind
  label: string
  target: PortalTarget
  /** Cancelling asks for a reason first (sheet); everything else is sent directly. */
  opensSheet: boolean
  /** Filled button for registering, outlined for the rest (mockup). */
  emphasis: 'primary' | 'secondary' | 'text'
}

export interface SessionView {
  chip: PortalStatus
  action: SessionAction | null
  enabled: boolean
  /** Why the action is not available (deadline, capacity, rule). */
  blocked: string | null
  hint: string | null
  unavailableReasons: string[] | null
}

const CANCEL_DEADLINE = 'Abmeldung nur noch direkt bei der Dienstleitung.'
const MAX_FREE_HINT = 'Alle Plätze sind vergeben. Du kommst auf die Warteliste.'

/** Name for button labels: the child's first name, nothing for the member's own account. */
export function personName(person: PortalPerson | null): string | null {
  return person && person.relation === 'child' ? person.first_name : null
}

function withName(name: string | null, verb: string): string {
  return name ? `${name} ${verb}` : verb.charAt(0).toUpperCase() + verb.slice(1)
}

export function chipFor(item: PortalSessionItem): PortalStatus {
  if (item.session_status === 'cancelled') return 'session-cancelled'
  const state = item.state
  if (!item.eligibility.ok && (state === 'no_response' || state === 'cancelled' || state === 'expected')) return 'unavailable'
  switch (state) {
    case 'expected': return 'expected'
    case 'no_response': return 'no-response'
    case 'registered': return item.mode === 'opt_out' ? 'expected' : 'registered'
    case 'waitlisted': return 'waitlist'
    case 'applied': return 'applied'
    case 'assigned': return 'assigned'
    case 'not_selected': return 'not-selected'
    default: return 'declined'
  }
}

function actionFor(item: PortalSessionItem, name: string | null): { action: SessionAction, flag: boolean, blocked: PortalSessionItem['cancel_blocked'] } | null {
  const cancel = (label: string, kind: ActionKind = 'cancel', target: PortalTarget = 'cancelled', opensSheet = false): ReturnType<typeof actionFor> => ({
    action: { kind, label, target, opensSheet, emphasis: 'secondary' }, flag: item.may_cancel, blocked: item.cancel_blocked,
  })
  const register = (label: string, kind: ActionKind, target: PortalTarget, emphasis: SessionAction['emphasis']): ReturnType<typeof actionFor> => ({
    action: { kind, label, target, opensSheet: false, emphasis }, flag: item.may_register, blocked: item.register_blocked,
  })
  switch (item.state) {
    case 'expected':
    case 'registered':
    case 'assigned':
      return cancel(withName(name, 'abmelden'), 'cancel', 'cancelled', true)
    case 'waitlisted': return cancel('Von der Warteliste abmelden', 'leave_waitlist')
    case 'applied': return cancel('Bewerbung zurückziehen', 'withdraw', 'withdrawn')
    case 'cancelled':
      if (item.mode === 'opt_out') return register('Abmeldung zurücknehmen', 'undo_cancel', 'registered', 'text')
      if (item.mode === 'assignment') return register(withName(name, 'bewerben'), 'apply', 'applied', 'primary')
      return register(withName(name, 'anmelden'), 'register', 'registered', 'primary')
    case 'no_response':
      if (item.mode === 'assignment') return register(withName(name, 'bewerben'), 'apply', 'applied', 'primary')
      return register(item.limited && item.free_places === 0 ? withName(name, 'auf die Warteliste setzen') : withName(name, 'anmelden'), 'register', 'registered', 'primary')
    default: return null
  }
}

export function describeSession(item: PortalSessionItem, person: PortalPerson | null): SessionView {
  const chip = chipFor(item)
  const view: SessionView = { chip, action: null, enabled: false, blocked: null, hint: null, unavailableReasons: null }
  if (chip === 'unavailable') {
    view.unavailableReasons = item.eligibility.reasons.length ? item.eligibility.reasons : [item.eligibility.audience_notice ?? 'Voraussetzung nicht erfüllt.']
    return view
  }
  if (item.session_status === 'cancelled') { view.hint = 'Dieser Dienst wurde abgesagt.'; return view }
  const found = actionFor(item, personName(person))
  if (found) {
    if (found.flag) {
      view.action = found.action
      view.enabled = true
    } else if (found.blocked) {
      view.action = found.action
      view.blocked = found.blocked.code === 'deadline_passed' && found.action.target !== 'registered' && found.action.target !== 'applied'
        ? CANCEL_DEADLINE
        : found.blocked.detail
    }
  }
  if (item.state === 'waitlisted' && item.waitlist_position) view.hint = `Warteliste, Platz ${item.waitlist_position}`
  else if (item.state === 'cancelled' && item.reason_category) view.hint = `Grund: ${reasonLabel(item.reason_category)}`
  else if (item.state === 'no_response' && item.limited && item.free_places === 0 && view.enabled) view.hint = MAX_FREE_HINT
  return view
}

const WEEKDAYS = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']

function parseDay(date: string): Date {
  const [y, m, d] = date.split('-').map(Number)
  return new Date(y!, (m ?? 1) - 1, d)
}

/** "Di 14.10." (or with year when asked). */
export function formatDay(date: string, withYear = false): string {
  const d = parseDay(date)
  const base = `${WEEKDAYS[d.getDay()]} ${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.`
  return withYear ? `${base}${d.getFullYear()}` : base
}

export function formatTimeRange(start: string | null, end: string | null): string {
  if (!start) return ''
  return end ? `${start.slice(0, 5)}–${end.slice(0, 5)}` : start.slice(0, 5)
}

/** "Do 16.10., 09:00" for an ISO timestamp. */
export function formatDeadline(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const day = `${WEEKDAYS[d.getDay()]} ${String(d.getDate()).padStart(2, '0')}.${String(d.getMonth() + 1).padStart(2, '0')}.`
  return `${day}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function sessionMeta(item: PortalSessionItem): string {
  return [`${formatDay(item.date)}`, formatTimeRange(item.start_time, item.end_time), item.place].filter(Boolean).join(' · ')
}

export function monthKey(date: string): string {
  return date.slice(0, 7)
}

export function monthLabel(key: string): string {
  const [y, m] = key.split('-').map(Number)
  return new Intl.DateTimeFormat('de-DE', { month: 'long', year: 'numeric' }).format(new Date(y!, (m ?? 1) - 1, 1))
}

export function placesText(item: PortalSessionItem): { text: string, ratio: number | null } | null {
  if (!item.limited || item.mode === 'opt_out' || item.free_places === null) return null
  const max = item.max_participants ?? null
  if (item.free_places === 0) return { text: 'Keine Plätze frei', ratio: max ? 1 : null }
  if (max) return { text: `Noch ${item.free_places} von ${max} Plätzen frei`, ratio: (max - item.free_places) / max }
  return { text: item.free_places === 1 ? 'Noch 1 Platz frei' : `Noch ${item.free_places} Plätze frei`, ratio: null }
}

/** Last day for the next action: registration deadline while it is open, else the cancellation deadline. */
export function deadlineText(item: PortalSessionItem): string | null {
  const open = item.state === 'no_response' || item.state === 'cancelled' && item.mode !== 'opt_out'
  const iso = open ? item.deadlines.registration_closes_at : item.deadlines.cancellation_closes_at
  if (!iso) return null
  return `${open ? 'Anmeldeschluss' : 'Abmeldeschluss'} ${formatDeadline(iso)}`
}

export type BannerTone = 'success' | 'info' | 'neutral' | 'warning'

/** Status sentence for the detail banner ("Mia ist angemeldet", "Du bist angemeldet"). */
export function statusBanner(item: PortalSessionItem, person: PortalPerson | null): { text: string, tone: BannerTone, icon: string } {
  const name = personName(person)
  const is = (adj: string) => (name ? `${name} ist ${adj}` : `Du bist ${adj}`)
  if (item.session_status === 'cancelled') return { text: 'Dieser Dienst wurde abgesagt', tone: 'warning', icon: 'pi pi-ban' }
  if (chipFor(item) === 'unavailable') return { text: 'Teilnahme nicht möglich', tone: 'neutral', icon: 'pi pi-lock' }
  switch (item.state) {
    case 'expected': return { text: is('eingeplant'), tone: 'success', icon: 'pi pi-check' }
    case 'registered': return { text: is(item.mode === 'opt_out' ? 'eingeplant' : 'angemeldet'), tone: 'success', icon: 'pi pi-check' }
    case 'waitlisted': return { text: item.waitlist_position ? `Warteliste, Platz ${item.waitlist_position}` : 'Auf der Warteliste', tone: 'info', icon: 'pi pi-clock' }
    case 'applied': return { text: name ? `${name} hat sich beworben` : 'Du hast dich beworben', tone: 'info', icon: 'pi pi-send' }
    case 'assigned': return { text: is('zugeteilt'), tone: 'success', icon: 'pi pi-check-circle' }
    case 'not_selected': return { text: name ? `${name} wurde nicht berücksichtigt` : 'Du wurdest nicht berücksichtigt', tone: 'neutral', icon: 'pi pi-minus-circle' }
    case 'cancelled': return { text: is('abgemeldet'), tone: 'warning', icon: 'pi pi-times' }
    default: return { text: 'Noch keine Rückmeldung', tone: 'neutral', icon: 'pi pi-circle' }
  }
}
