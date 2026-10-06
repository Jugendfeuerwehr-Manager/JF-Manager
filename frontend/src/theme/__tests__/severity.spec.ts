import { describe, expect, it } from 'vitest'

/**
 * PrimeVue 4 calls the warning tone `warn`; `warning` silently falls back to the
 * primary colour, so a warning looked like the organisation's brand colour.
 */
const sources = import.meta.glob('/src/**/*.vue', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const PRIME_COMPONENT_WITH_WARNING = /<(Tag|Badge|Button|Message|Chip|ToggleButton)\b[^>]*\bseverity="warning"/g

describe('PrimeVue severities', () => {
  it('never passes the PrimeVue 3 name "warning" to PrimeVue components', () => {
    const offenders = Object.entries(sources).flatMap(([file, source]) =>
      [...source.matchAll(PRIME_COMPONENT_WITH_WARNING)].map((match) => `${file}: <${match[1]} … severity="warning">`),
    )
    expect(offenders).toEqual([])
  })

  it('uses the PrimeVue 4 button class for warnings', () => {
    const offenders = Object.entries(sources).filter(([, source]) => source.includes('p-button-warning')).map(([file]) => file)
    expect(offenders).toEqual([])
  })
})
