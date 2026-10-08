import { describe, expect, it } from 'vitest'
import { qualificationStatus } from '../qualificationStatus'
import type { Qualification } from '@/types/qualifications'

const today = new Date(2026, 9, 6)
const q = (date_expires: string | null, is_expired = false) => ({ date_expires, is_expired } as Qualification)

describe('qualification status wording', () => {
  it('names the remaining days and escalates only inside 30 days', () => {
    expect(qualificationStatus(q('2026-10-06'), today)).toEqual({ label: 'Läuft heute ab', severity: 'warning' })
    expect(qualificationStatus(q('2026-10-07'), today)).toEqual({ label: 'Läuft in 1 Tag ab', severity: 'warning' })
    expect(qualificationStatus(q('2026-11-05'), today).severity).toBe('warning')
    expect(qualificationStatus(q('2026-12-20'), today)).toEqual({ label: 'Läuft in 75 Tagen ab', severity: 'info' })
    expect(qualificationStatus(q('2027-06-01'), today)).toEqual({ label: 'Gültig', severity: 'success' })
  })

  it('separates expired and unlimited qualifications', () => {
    expect(qualificationStatus(q('2026-10-01', true), today)).toEqual({ label: 'Abgelaufen', severity: 'danger' })
    expect(qualificationStatus(q(null), today)).toEqual({ label: 'Unbefristet gültig', severity: 'success' })
  })
})
