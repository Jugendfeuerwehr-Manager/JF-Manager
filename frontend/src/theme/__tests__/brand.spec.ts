import { describe, expect, it, vi } from 'vitest'
import { contrastRatio } from '../contrast'
import { brand, roles } from '../palette'
import { COLOR_SCHEMES, DEFAULT_BRAND_COLOR, brandPresetOverride, buildScale, normalizeBrandColor, resolveBrand } from '../brand'

const awkward = ['#ffff00', '#00ff00', '#ffffff', '#000000', '#000080', '#888888', '#f0abfc', '#22d3ee']

describe('brand colour', () => {
  it('keeps the hand-tuned Feuerwehrrot scale as default', () => {
    expect(buildScale(DEFAULT_BRAND_COLOR)).toEqual(brand)
    expect(resolveBrand(null).light.color).toBe(roles.light.primary)
    expect(resolveBrand(undefined).dark.color).toBe(roles.dark.primary)
  })

  it('rejects anything but #rrggbb', () => {
    for (const value of ['red', '#fff', 'url(x)', '#12345g', '', '  ']) {
      expect(normalizeBrandColor(value)).toBe(DEFAULT_BRAND_COLOR)
    }
    expect(normalizeBrandColor(' #1D4ED8 ')).toBe('#1d4ed8')
  })

  it.each([...COLOR_SCHEMES.map(s => s.color), ...awkward])('keeps WCAG AA for %s in light and dark mode', color => {
    const { light, dark } = resolveBrand(color)
    expect(contrastRatio(light.onColor, light.color)).toBeGreaterThanOrEqual(4.5)
    expect(contrastRatio(light.onColor, light.hover)).toBeGreaterThanOrEqual(4.5)
    expect(contrastRatio(light.color, roles.light.ground)).toBeGreaterThanOrEqual(4.5)
    expect(contrastRatio(light.color, roles.light.card)).toBeGreaterThanOrEqual(4.5)
    expect(contrastRatio(dark.color, roles.dark.card)).toBeGreaterThanOrEqual(4.5)
    expect(contrastRatio(dark.color, roles.dark.ground)).toBeGreaterThanOrEqual(4.5)
    expect(contrastRatio(dark.onColor, dark.color)).toBeGreaterThanOrEqual(4.5)
    // Highlighted rows and active navigation: primary-800 text on primary-50
    const scale = resolveBrand(color).scale
    expect(contrastRatio(light.highlightText, scale[50])).toBeGreaterThanOrEqual(4.5)
    expect(contrastRatio(light.highlightFocusText, scale[100])).toBeGreaterThanOrEqual(4.5)
  })

  it('uses the chosen colour itself when it is already accessible', () => {
    expect(resolveBrand('#1d4ed8').light.color).toBe('#1d4ed8')
    expect(resolveBrand('#ffff00').light.color).not.toBe('#ffff00')
  })

  it('builds a preset fragment for primary scale and both colour schemes', () => {
    const override = brandPresetOverride('#0f766e')
    expect(Object.keys(override.semantic.primary)).toHaveLength(11)
    expect(override.semantic.colorScheme.light.primary.color).toBe(resolveBrand('#0f766e').light.color)
    expect(override.semantic.colorScheme.dark.primary.contrastColor).toBe(roles.dark.onPrimary)
  })
})

describe('applyBrandColor', () => {
  it('updates the preset once per colour and remembers it for the next load', async () => {
    const updatePreset = vi.fn()
    vi.doMock('@primeuix/themes', () => ({ updatePreset }))
    const { applyBrandColor, applyRememberedBrandColor, currentBrandColor } = await import('../applyBrand')
    document.head.innerHTML = '<meta name="theme-color" content="#b91c1c">'
    applyBrandColor('#1D4ED8')
    applyBrandColor('#1d4ed8')
    expect(updatePreset).toHaveBeenCalledTimes(1)
    expect(currentBrandColor()).toBe('#1d4ed8')
    expect(document.querySelector('meta[name="theme-color"]')?.getAttribute('content')).toBe('#1d4ed8')
    expect(localStorage.getItem('jfm-brand-color')).toBe('#1d4ed8')
    applyBrandColor('not-a-colour')
    expect(currentBrandColor()).toBe(DEFAULT_BRAND_COLOR)
    localStorage.setItem('jfm-brand-color', '#0f766e')
    applyRememberedBrandColor()
    expect(currentBrandColor()).toBe('#0f766e')
    vi.doUnmock('@primeuix/themes')
  })
})
