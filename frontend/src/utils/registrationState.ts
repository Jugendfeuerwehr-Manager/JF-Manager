import type { RegistrationPerson, RegistrationState } from '@/types/servicebook'

/** Text and symbol for each registration state; colour alone never carries the meaning. */
export const REGISTRATION_STATE: Record<RegistrationState, { label: string; icon: string; tone: 'ok' | 'warn' | 'bad' | 'neutral' }> = {
  expected: { label: 'erwartet', icon: 'pi pi-check', tone: 'neutral' },
  no_response: { label: 'keine Rückmeldung', icon: 'pi pi-question-circle', tone: 'neutral' },
  registered: { label: 'angemeldet', icon: 'pi pi-plus-circle', tone: 'ok' },
  waitlisted: { label: 'Warteliste', icon: 'pi pi-clock', tone: 'warn' },
  applied: { label: 'beworben', icon: 'pi pi-send', tone: 'warn' },
  assigned: { label: 'zugeteilt', icon: 'pi pi-check-circle', tone: 'ok' },
  not_selected: { label: 'nicht berücksichtigt', icon: 'pi pi-minus-circle', tone: 'neutral' },
  cancelled: { label: 'abgemeldet', icon: 'pi pi-times-circle', tone: 'bad' },
}

const REASONS: Record<string, string> = {
  krankheit: 'Krankheit',
  schule_beruf: 'Schule/Beruf',
  urlaub: 'Urlaub',
  familie: 'Familie',
  sonstiges: 'Sonstiges',
}

export function reasonLabel(category: string | null | undefined): string {
  if (!category) return ''
  return REASONS[category] ?? category
}

export function registrationLabel(person: RegistrationPerson): string {
  if (!person.state) return person.in_target ? '' : 'Gast'
  const base = REGISTRATION_STATE[person.state].label
  if (person.state === 'waitlisted' && person.waitlist_position) return `${base} (Platz ${person.waitlist_position})`
  return base
}

export function formatDateTime(value: string | null): string {
  if (!value) return ''
  const d = new Date(value)
  return `${d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })} ${d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}`
}

const SOURCES: Record<string, string> = {
  portal_parent: 'Elternkonto',
  portal_member: 'selbst',
  staff: 'Betreuende',
}

export function sourceLabel(source: string | null | undefined): string {
  if (!source) return ''
  return SOURCES[source] ?? source
}
