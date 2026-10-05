import { updatePreset } from '@primeuix/themes'
import { brandPresetOverride, normalizeBrandColor, resolveBrand, DEFAULT_BRAND_COLOR } from './brand'

const STORAGE_KEY = 'jfm-brand-color'
let applied: string = DEFAULT_BRAND_COLOR

/** Applies an organisation colour to all PrimeVue and app tokens at runtime. */
export function applyBrandColor(value: string | null | undefined) {
  const color = normalizeBrandColor(value)
  if (color !== applied) {
    updatePreset(brandPresetOverride(color))
    applied = color
  }
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', resolveBrand(color).light.color)
  try {
    localStorage.setItem(STORAGE_KEY, color)
  } catch {
    // Private mode or blocked storage: the server value is applied on every load anyway.
  }
}

/** Last known colour of this browser, so the first paint already matches. */
export function applyRememberedBrandColor() {
  let remembered: string | null = null
  try {
    remembered = localStorage.getItem(STORAGE_KEY)
  } catch {
    remembered = null
  }
  if (remembered) applyBrandColor(remembered)
}

export function currentBrandColor() {
  return applied
}
