/**
 * Common size series for generating clothing and shoe variants.
 */

export interface SizePreset {
  key: string
  label: string
  values: string[]
}

function range(from: number, to: number, step: number): string[] {
  const values: string[] = []
  for (let value = from; value <= to; value += step) {
    values.push(String(value))
  }
  return values
}

export const SIZE_PRESETS: SizePreset[] = [
  { key: 'children', label: 'Kindergrößen (98–176)', values: range(98, 176, 6) },
  { key: 'letter', label: 'Internationale Größen (S–XXXL)', values: ['S', 'M', 'L', 'XL', 'XXL', 'XXXL'] },
  { key: 'men', label: 'Konfektionsgrößen Herren (44–64)', values: range(44, 64, 2) },
  { key: 'women', label: 'Konfektionsgrößen Damen (32–50)', values: range(32, 50, 2) },
  { key: 'shoes', label: 'Schuhgrößen (30–48)', values: range(30, 48, 1) }
]

/**
 * Split free text like "XS, 4XL; 182" into trimmed, unique values.
 */
export function parseSizeValues(input: string): string[] {
  const seen = new Set<string>()
  const values: string[] = []
  for (const raw of input.split(/[,;\n]/)) {
    const value = raw.trim()
    if (value && !seen.has(value.toLowerCase())) {
      seen.add(value.toLowerCase())
      values.push(value)
    }
  }
  return values
}
