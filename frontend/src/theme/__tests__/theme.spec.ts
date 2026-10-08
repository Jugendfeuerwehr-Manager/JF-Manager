import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { contrastRatio } from '../contrast'
import { brand, roles, surface, type ColorScheme } from '../palette'
import { JfPreset } from '../preset'

const schemes: ColorScheme[] = ['light', 'dark']

describe('design palette', () => {
  it('keeps the fixed brand values', () => {
    expect(roles.light.ground).toBe('#f5f7fa')
    expect(roles.light.card).toBe('#ffffff')
    expect(roles.light.text).toBe('#172033')
    expect(brand[700]).toBe('#b91c1c')
    expect(roles.light.primary).toBe(brand[700])
  })

  it.each(schemes)('meets WCAG AA for text in %s mode', scheme => {
    const role = roles[scheme]
    for (const background of [role.ground, role.card]) {
      expect(contrastRatio(role.text, background)).toBeGreaterThanOrEqual(4.5)
      expect(contrastRatio(role.textMuted, background)).toBeGreaterThanOrEqual(4.5)
      expect(contrastRatio(role.primary, background)).toBeGreaterThanOrEqual(4.5)
    }
    expect(contrastRatio(role.onPrimary, role.primary)).toBeGreaterThanOrEqual(4.5)
    expect(contrastRatio(role.onPrimary, role.primaryHover)).toBeGreaterThanOrEqual(4.5)
  })

  it.each(schemes)('gives form controls a 3:1 boundary in %s mode', scheme => {
    const role = roles[scheme]
    for (const background of [role.ground, role.card]) {
      expect(contrastRatio(role.controlBorder, background)).toBeGreaterThanOrEqual(3)
    }
  })

  it('computes known WCAG ratios', () => {
    expect(contrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 5)
    expect(contrastRatio(surface[0], surface[0])).toBe(1)
  })
})

describe('PrimeVue preset', () => {
  it('uses Feuerwehrrot as primary and the neutral surface scale', () => {
    const { semantic } = JfPreset as unknown as { semantic: Record<string, unknown> }
    expect(semantic).toMatchObject({
      primary: { 700: '#b91c1c' },
      colorScheme: {
        light: { primary: { color: roles.light.primary }, surface: { 50: roles.light.ground } },
        dark: { content: { background: roles.dark.card } },
      },
    })
  })
})

describe('token stylesheet', () => {
  const css = readFileSync(resolve(__dirname, '../../assets/tokens.css'), 'utf-8')

  it.each([
    '--surface-card',
    '--surface-border',
    '--surface-ground',
    '--surface-hover',
    '--primary-color',
    '--text-color',
    '--text-color-secondary',
    '--border-radius',
    '--p-surface-ground',
  ])('maps the legacy variable %s', name => {
    expect(css).toMatch(new RegExp(`\\s${name}:`))
  })

  it('does not load external fonts', () => {
    expect(css).not.toMatch(/@import|url\(/)
  })
})
