import { describe, expect, it } from 'vitest'
import baseline from './fixedColorBaseline.json'

/**
 * DES-01.11c ratchet: colours come from the design tokens. Fixed hex/rgb values
 * may only shrink. When you remove some, lower the file's entry in
 * fixedColorBaseline.json; new files start at zero.
 */
const sources = import.meta.glob('/src/**/*.vue', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const LITERAL_COLOR = /#[0-9a-fA-F]{3,8}\b|rgba?\(/g
const limits = baseline as Record<string, number>

describe('fixed colours', () => {
  it('never adds fixed colours beyond the per-file baseline', () => {
    const offenders = Object.entries(sources).flatMap(([file, source]) => {
      const count = source.match(LITERAL_COLOR)?.length ?? 0
      const limit = limits[file] ?? 0
      return count > limit ? [`${file}: ${count} fixed colours, allowed ${limit}`] : []
    })
    expect(offenders).toEqual([])
  })

  it('keeps the baseline free of removed files', () => {
    expect(Object.keys(limits).filter((file) => !(file in sources))).toEqual([])
  })
})
