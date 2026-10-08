// Monaco ships with the app: loading it from a CDN would need a script-src
// exception in the Content-Security-Policy and run code we do not version.
// Monaco references its workers via `new URL(..., import.meta.url)`, which
// Vite bundles as same-origin files.
import type * as Monaco from 'monaco-editor'

let pending: Promise<typeof Monaco> | null = null

export function loadMonaco(): Promise<typeof Monaco> {
  pending ??= import('monaco-editor')
  return pending
}
