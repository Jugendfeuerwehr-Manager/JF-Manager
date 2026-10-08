import { describe, expect, it } from 'vitest'
import { contrastRatio } from '@/theme/contrast'
import { roles, type ColorScheme } from '@/theme/palette'
import { BLOCK_TINT_PERCENT, mixHex, safeBlockColor } from '../blockColor'

const schemes: ColorScheme[] = ['light', 'dark']
const EXTREMES = ['#ffffff', '#000000', '#ffff00', '#00ff00', '#0000ff', '#ff0000', '#b91c1c', '#7d8899']

describe('block colours', () => {
  it('accepts only plain hex colours', () => {
    expect(safeBlockColor('#3B82F6')).toBe('#3b82f6')
    expect(safeBlockColor('#abc')).toBe('#abc')
    for (const value of ['', null, undefined, 'red', '#12345', 'url(x)', '#fff; background: url(x)', 'var(--x)']) {
      expect(safeBlockColor(value)).toBeNull()
    }
  })

  it('matches CSS color-mix for the tile tint', () => {
    expect(mixHex('#000000', '#ffffff', 50)).toBe('#808080')
    expect(mixHex('#fff', '#000000', 100)).toBe('#ffffff')
  })

  it.each(schemes)('keeps tile text readable for any chosen colour in %s mode', (scheme) => {
    const role = roles[scheme]
    for (const color of EXTREMES) {
      const tile = mixHex(color, role.card, BLOCK_TINT_PERCENT)
      expect(contrastRatio(role.text, tile), `${color} on ${scheme}`).toBeGreaterThanOrEqual(4.5)
    }
  })
})
