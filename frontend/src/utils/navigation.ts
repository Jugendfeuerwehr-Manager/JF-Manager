/** Full page load; clears every in-memory store and leaves the SPA when needed. */
export function hardNavigate(path: string): void {
  window.location.assign(path)
}

/** Same-origin relative paths only; everything else falls back to the start page. */
export function safeReturnPath(value: unknown): string {
  if (typeof value !== 'string') return '/'
  if (!value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return '/'
  if (/[\u0000-\u001f]/.test(value) || value.startsWith('/login')) return '/'
  return value
}

/** Backend pages (e.g. Django admin) are not SPA routes. */
export function isServerPath(path: string): boolean {
  return /^\/(admin|api)(\/|$)/.test(path)
}
