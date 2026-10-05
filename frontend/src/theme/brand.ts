import { contrastRatio } from './contrast'
import { brand as defaultScale, roles } from './palette'

/**
 * Adjustable colour scheme (DES-01.6): organisations pick one base colour,
 * the app derives a full scale and chooses the shades for buttons, links and
 * focus so that text on and next to them keeps WCAG AA contrast in light and
 * dark mode. Status colours (success, warning, danger) stay fixed.
 */

export type Shade = 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 | 950
export type ColorScale = Record<Shade, string>

export interface ColorSchemeOption {
  key: string
  label: string
  color: string
}

export const DEFAULT_BRAND_COLOR = defaultScale[700]

/** Ready-made schemes; any other valid hex colour is accepted as well. */
export const COLOR_SCHEMES: ColorSchemeOption[] = [
  { key: 'feuerwehrrot', label: 'Feuerwehrrot', color: DEFAULT_BRAND_COLOR },
  { key: 'blau', label: 'Blau', color: '#1d4ed8' },
  { key: 'gruen', label: 'Grün', color: '#15803d' },
  { key: 'orange', label: 'Orange', color: '#c2410c' },
  { key: 'petrol', label: 'Petrol', color: '#0f766e' },
]

const HEX = /^#[0-9a-f]{6}$/i

export function normalizeBrandColor(value: string | null | undefined): string {
  const color = (value ?? '').trim().toLowerCase()
  return HEX.test(color) ? color : DEFAULT_BRAND_COLOR
}

/** Mix weights: positive towards white, negative towards black. */
const MIX: Record<Shade, number> = {
  50: 0.95, 100: 0.9, 200: 0.75, 300: 0.55, 400: 0.3, 500: 0,
  600: -0.15, 700: -0.3, 800: -0.45, 900: -0.58, 950: -0.75,
}

export function buildScale(base: string): ColorScale {
  const color = normalizeBrandColor(base)
  if (color === DEFAULT_BRAND_COLOR) return { ...defaultScale }
  const scale = {} as ColorScale
  for (const [shade, weight] of Object.entries(MIX)) {
    scale[Number(shade) as Shade] = weight >= 0 ? mix(color, '#ffffff', weight) : mix(color, '#000000', -weight)
  }
  return scale
}

export interface BrandRoles {
  scale: ColorScale
  light: { color: string; hover: string; active: string; onColor: string; highlightText: string; highlightFocusText: string }
  dark: { color: string; hover: string; active: string; onColor: string }
}

const LIGHT_CANDIDATES: Shade[] = [500, 600, 700, 800, 900]
const DARK_CANDIDATES: Shade[] = [400, 300, 200, 100]
const HIGHLIGHT_TEXT_CANDIDATES: Shade[] = [800, 900, 950]

/**
 * Picks the shades the UI uses. In light mode the colour must carry white
 * text and stand out on the page ground; in dark mode it must stand out on
 * cards and carry dark text.
 */
export function resolveBrand(base: string | null | undefined): BrandRoles {
  const scale = buildScale(normalizeBrandColor(base))
  const light = roles.light
  const dark = roles.dark

  const lightIndex = LIGHT_CANDIDATES.findIndex(shade =>
    contrastRatio(light.onPrimary, scale[shade]) >= 4.5 &&
    contrastRatio(scale[shade], light.ground) >= 4.5)
  const darkIndex = DARK_CANDIDATES.findIndex(shade =>
    contrastRatio(scale[shade], dark.card) >= 4.5 &&
    contrastRatio(scale[shade], dark.ground) >= 4.5 &&
    contrastRatio(dark.onPrimary, scale[shade]) >= 4.5)

  // Selected rows and active navigation: text on the lightest tints.
  const highlightIndex = HIGHLIGHT_TEXT_CANDIDATES.findIndex(shade =>
    contrastRatio(scale[shade], scale[50]) >= 4.5 && contrastRatio(scale[shade], scale[100]) >= 4.5)

  if (lightIndex < 0 || darkIndex < 0 || highlightIndex < 0) return resolveBrand(DEFAULT_BRAND_COLOR)

  const lightPick = (offset: number) => scale[LIGHT_CANDIDATES[Math.min(lightIndex + offset, LIGHT_CANDIDATES.length - 1)]!]
  const darkPick = (offset: number) => scale[DARK_CANDIDATES[Math.min(darkIndex + offset, DARK_CANDIDATES.length - 1)]!]

  return {
    scale,
    light: {
      color: lightPick(0),
      hover: lightPick(1),
      active: lightPick(2),
      onColor: light.onPrimary,
      highlightText: scale[HIGHLIGHT_TEXT_CANDIDATES[highlightIndex]!],
      highlightFocusText: scale[HIGHLIGHT_TEXT_CANDIDATES[Math.min(highlightIndex + 1, HIGHLIGHT_TEXT_CANDIDATES.length - 1)]!],
    },
    dark: { color: darkPick(0), hover: darkPick(1), active: darkPick(2), onColor: dark.onPrimary },
  }
}

/** Semantic preset fragment for PrimeVue's `updatePreset`. */
export function brandPresetOverride(base: string | null | undefined) {
  const brandRoles = resolveBrand(base)
  return {
    semantic: {
      primary: brandRoles.scale,
      colorScheme: {
        light: {
          primary: {
            color: brandRoles.light.color,
            contrastColor: brandRoles.light.onColor,
            hoverColor: brandRoles.light.hover,
            activeColor: brandRoles.light.active,
          },
          highlight: {
            color: brandRoles.light.highlightText,
            focusColor: brandRoles.light.highlightFocusText,
          },
        },
        dark: {
          primary: {
            color: brandRoles.dark.color,
            contrastColor: brandRoles.dark.onColor,
            hoverColor: brandRoles.dark.hover,
            activeColor: brandRoles.dark.active,
          },
        },
      },
    },
  }
}

function mix(from: string, to: string, weight: number): string {
  const a = channels(from)
  const b = channels(to)
  return '#' + a.map((value, index) => Math.round(value + (b[index]! - value) * weight).toString(16).padStart(2, '0')).join('')
}

function channels(hex: string): number[] {
  return [1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16))
}
