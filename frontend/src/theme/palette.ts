/**
 * Raw colour values of the JF-Manager design system (DES-01).
 *
 * The PrimeVue preset and the contrast tests are both built from these
 * constants, so a change here is checked against WCAG AA automatically.
 */

/** Feuerwehrrot scale; 700 is the brand colour #B91C1C. */
export const brand = {
  50: '#fef2f2',
  100: '#fee2e2',
  200: '#fecaca',
  300: '#fca5a5',
  400: '#f87171',
  500: '#ef4444',
  600: '#dc2626',
  700: '#b91c1c',
  800: '#991b1b',
  900: '#7f1d1d',
  950: '#450a0a',
} as const

/** Cool neutral scale; 50 is the page ground, 900 the body text colour. */
export const surface = {
  0: '#ffffff',
  50: '#f5f7fa',
  100: '#eef1f5',
  200: '#e3e8ef',
  300: '#cdd5df',
  400: '#7d8899',
  500: '#697586',
  600: '#4b5565',
  700: '#364152',
  800: '#202939',
  900: '#172033',
  950: '#0d121c',
} as const

/** Semantic roles per colour scheme, used by the preset and the app tokens. */
export const roles = {
  light: {
    ground: surface[50],
    card: surface[0],
    text: surface[900],
    textMuted: surface[600],
    border: surface[200],
    controlBorder: surface[400],
    primary: brand[700],
    primaryHover: brand[800],
    primaryActive: brand[900],
    onPrimary: surface[0],
  },
  dark: {
    ground: surface[950],
    card: surface[900],
    text: surface[0],
    textMuted: surface[400],
    border: surface[700],
    controlBorder: surface[500],
    primary: brand[400],
    primaryHover: brand[300],
    primaryActive: brand[200],
    onPrimary: surface[950],
  },
} as const

export type ColorScheme = keyof typeof roles
