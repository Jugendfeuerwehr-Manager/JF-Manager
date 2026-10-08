import { describe, expect, it } from 'vitest'

/**
 * App.vue renders the one Toast and the one ungrouped ConfirmDialog. Extra
 * copies show every toast twice and stack identical confirmation dialogs.
 */
const sources = import.meta.glob('/src/**/*.vue', { query: '?raw', import: 'default', eager: true }) as Record<string, string>

describe('global overlays', () => {
  it('keeps the ungrouped Toast and ConfirmDialog in App.vue only', () => {
    const offenders = Object.entries(sources)
      .filter(([file]) => file !== '/src/App.vue')
      .filter(([, source]) => /<Toast\s*\/>|<ConfirmDialog\s*\/>/.test(source))
      .map(([file]) => file)
    expect(offenders).toEqual([])
  })
})
