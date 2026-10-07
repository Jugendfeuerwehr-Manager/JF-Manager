import { describe, expect, it } from 'vitest'
import { SIZE_PRESETS, parseSizeValues } from '../sizePresets'

describe('sizePresets', () => {
  it('provides children, letter, tailoring and shoe sizes', () => {
    const byKey = Object.fromEntries(SIZE_PRESETS.map((preset) => [preset.key, preset.values]))

    expect(byKey.children).toEqual(['98', '104', '110', '116', '122', '128', '134', '140', '146', '152', '158', '164', '170', '176'])
    expect(byKey.letter).toEqual(['S', 'M', 'L', 'XL', 'XXL', 'XXXL'])
    expect(byKey.men?.[0]).toBe('44')
    expect(byKey.men?.at(-1)).toBe('64')
    expect(byKey.shoes).toHaveLength(19)
  })

  it('parses free text into trimmed unique values', () => {
    expect(parseSizeValues(' XS, 4xl;4XL\n182 ,, ')).toEqual(['XS', '4xl', '182'])
  })
})
