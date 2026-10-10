/** tel: link that keeps only digits and a leading plus; empty when no digits remain. */
export function telHref(value: string | null | undefined): string {
  const digits = (value ?? '').trim().replace(/[^\d+]/g, '')
  const normalised = (digits.startsWith('+') ? '+' : '') + digits.replace(/\+/g, '')
  return normalised ? `tel:${normalised}` : ''
}
