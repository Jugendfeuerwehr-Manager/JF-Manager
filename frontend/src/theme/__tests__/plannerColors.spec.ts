import { describe, expect, it } from 'vitest'

/**
 * DES-01.10b: the training planner (grid, tiles, library sidebar and their badges)
 * takes every colour from the design tokens. User-chosen block colours arrive as
 * data and are validated in components/training/utils/blockColor.ts.
 */
const sources = import.meta.glob(
  [
    '/src/components/training/organisms/SwimlaneEditor.vue',
    '/src/components/training/molecules/TrainingBlockTile.vue',
    '/src/components/training/molecules/LibraryBlockPicker.vue',
    '/src/components/training/atoms/BlockDurationBadge.vue',
    '/src/components/training/atoms/LibraryBlockCategoryBadge.vue',
    '/src/components/training/atoms/BlockEditor.vue',
  ],
  { query: '?raw', import: 'default', eager: true },
) as Record<string, string>
const LITERAL_COLOR = /#[0-9a-fA-F]{3,8}\b|rgba?\(/g

describe('planner colours', () => {
  it('covers all planner files', () => {
    expect(Object.keys(sources)).toHaveLength(6)
  })

  it('uses tokens instead of fixed colours', () => {
    const offenders = Object.entries(sources).flatMap(([file, source]) =>
      [...source.matchAll(LITERAL_COLOR)].map((match) => `${file}: ${match[0]}`),
    )
    expect(offenders).toEqual([])
  })
})
