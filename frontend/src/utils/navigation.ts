/** A path on this origin: no scheme, no protocol-relative `//`, no backslash or control characters. */
function isSameOriginPath(value: string): boolean {
  return value.startsWith('/') && !value.startsWith('//') && !value.includes('\\') && !/[\u0000-\u001f]/.test(value)
}

/** Full page load; clears every in-memory store and leaves the SPA when needed. Same-origin paths only. */
export function hardNavigate(path: string): void {
  window.location.assign(isSameOriginPath(path) ? path : '/')
}

/** Same-origin relative paths only; everything else falls back to the start page. */
export function safeReturnPath(value: unknown): string {
  if (typeof value !== 'string' || !isSameOriginPath(value) || value.startsWith('/login')) return '/'
  return value
}

/** Backend pages (e.g. Django admin) are not SPA routes. */
export function isServerPath(path: string): boolean {
  return /^\/(admin|api)(\/|$)/.test(path)
}
