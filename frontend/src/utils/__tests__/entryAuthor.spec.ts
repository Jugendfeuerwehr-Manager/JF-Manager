import { describe, expect, it } from 'vitest'
import { entryAuthorLabel } from '@/utils/entryAuthor'

describe('entryAuthorLabel', () => {
  it('names author and date', () => {
    expect(entryAuthorLabel('Lena Leiterin', '2026-11-24T10:15:00Z')).toBe('Angelegt von Lena Leiterin am 24.11.2026')
  })

  it('shows only the author when the date is missing', () => {
    expect(entryAuthorLabel('Lena Leiterin', null)).toBe('Angelegt von Lena Leiterin')
  })

  it('shows only the date for entries without a recorded author', () => {
    expect(entryAuthorLabel(null, '2026-11-24T10:15:00Z')).toBe('Angelegt am 24.11.2026')
  })

  it('is empty for old entries without author and date', () => {
    expect(entryAuthorLabel(null, null)).toBe('')
    expect(entryAuthorLabel(undefined, 'kein Datum')).toBe('')
  })
})
