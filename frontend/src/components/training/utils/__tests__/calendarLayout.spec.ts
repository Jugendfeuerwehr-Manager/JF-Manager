import { describe, expect, it } from 'vitest'
import { DEFAULT_SESSIONS_PER_CELL, sessionCapacity, visibleSessionCount } from '../calendarLayout'

describe('calendar cell capacity', () => {
  it('fits more entries into taller cells', () => {
    expect(sessionCapacity(90, 28)).toBe(3)
    expect(sessionCapacity(200, 28)).toBe(6)
  })

  it('always shows at least one entry and caps very tall cells', () => {
    expect(sessionCapacity(10, 28)).toBe(1)
    expect(sessionCapacity(5000, 28)).toBe(12)
  })

  it('falls back to the default without a measurement', () => {
    expect(sessionCapacity(Number.NaN, 28)).toBe(DEFAULT_SESSIONS_PER_CELL)
    expect(sessionCapacity(100, 0)).toBe(DEFAULT_SESSIONS_PER_CELL)
  })

  it('keeps a row for "+N weitere" only when entries overflow', () => {
    expect(visibleSessionCount(3, 3)).toBe(3)
    expect(visibleSessionCount(4, 3)).toBe(2)
    expect(visibleSessionCount(5, 1)).toBe(1)
  })
})
