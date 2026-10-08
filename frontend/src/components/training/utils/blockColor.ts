/**
 * Colours chosen for training and library blocks are free user input. The
 * planner only uses them as a light tint and a border (DES-01.10b); text keeps
 * the theme's text colour, so any chosen colour stays readable in both modes.
 */

/** Share of the block colour in the tile background, in percent. */
export const BLOCK_TINT_PERCENT = 14
/** Share of the block colour in the tile border, in percent. */
export const BLOCK_BORDER_PERCENT = 60

const HEX_COLOR = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i

/** Returns the colour when it is a plain hex value, otherwise null. */
export function safeBlockColor(value: string | null | undefined): string | null {
  const trimmed = value?.trim() ?? ''
  return HEX_COLOR.test(trimmed) ? trimmed.toLowerCase() : null
}

function channels(hex: string): [number, number, number] {
  const full = hex.length === 4 ? `#${[...hex.slice(1)].map(c => c + c).join('')}` : hex
  return [1, 3, 5].map(i => parseInt(full.slice(i, i + 2), 16)) as [number, number, number]
}

/** Same result as CSS `color-mix(in srgb, color pct%, base)` for hex colours. */
export function mixHex(color: string, base: string, percent: number): string {
  const a = channels(color)
  const b = channels(base)
  return `#${a.map((value, i) => Math.round((value * percent + b[i]! * (100 - percent)) / 100).toString(16).padStart(2, '0')).join('')}`
}
