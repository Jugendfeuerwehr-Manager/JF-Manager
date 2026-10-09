import type { PortalSessionItem } from '@/api/portal'

export function makeItem(over: Partial<PortalSessionItem> = {}): PortalSessionItem {
  return {
    id: 7, title: 'Orientierungsmarsch', date: '2026-10-18', start_time: '09:00:00', end_time: '13:00:00', place: 'Waldparkplatz',
    session_status: 'published', mode: 'opt_in', public_note: '', state: 'no_response', waitlist_position: null, reason_category: '', version: 0,
    late: false, deadlines: { registration_opens_at: null, registration_closes_at: '2026-10-16T09:00:00', cancellation_closes_at: '2026-10-17T18:00:00' },
    limited: true, free_places: 3, eligibility: { ok: true, reasons: [], audience_notice: null },
    may_register: true, may_cancel: false, register_blocked: null, cancel_blocked: null, ...over,
  }
}
