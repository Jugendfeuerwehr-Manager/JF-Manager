/**
 * Flexible date parsing for German-locale date inputs.
 * Supports dd.mm.yyyy, dd.mm.yy, dd-mm-yyyy, dd/mm/yyyy and ISO yyyy-mm-dd variants.
 */

const ISO_PATTERN = /^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$/
const DMY_PATTERN = /^(\d{1,2})[-./](\d{1,2})[-./](\d{2,4})$/

/** Normalizes a 2-digit year using the common 69/00 pivot (69-99 -> 1900s, 00-68 -> 2000s). */
function normalizeYear(year: number): number {
  if (year >= 100) return year
  return year <= 68 ? 2000 + year : 1900 + year
}

/** Builds a Date and rejects values that JS would otherwise silently roll over (e.g. 31.02). */
function buildDate(year: number, month: number, day: number): Date | null {
  if (month < 1 || month > 12 || day < 1 || day > 31) return null
  const date = new Date(year, month - 1, day)
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
    return null
  }
  return date
}

/**
 * Parses a date string entered by the user into a Date, trying several common formats
 * (German dd.mm.yyyy, dd-mm-yyyy, dd/mm/yyyy and ISO yyyy-mm-dd). Returns null if the
 * text does not match a known format or does not represent a valid calendar date.
 */
export function parseFlexibleDate(input: string): Date | null {
  const value = input.trim()
  if (!value) return null

  const isoMatch = value.match(ISO_PATTERN)
  if (isoMatch) {
    return buildDate(Number(isoMatch[1]), Number(isoMatch[2]), Number(isoMatch[3]))
  }

  const dmyMatch = value.match(DMY_PATTERN)
  if (dmyMatch) {
    const day = Number(dmyMatch[1])
    const month = Number(dmyMatch[2])
    const year = normalizeYear(Number(dmyMatch[3]))
    return buildDate(year, month, day)
  }

  return null
}

/** Formats a Date as a German dd.mm.yyyy string for display in text inputs. */
export function formatDateGerman(date: Date | null | undefined): string {
  if (!date) return ''
  const day = String(date.getDate()).padStart(2, '0')
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const year = date.getFullYear()
  return `${day}.${month}.${year}`
}
