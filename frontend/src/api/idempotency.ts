import type { AxiosError } from 'axios'

/**
 * Stable `Idempotency-Key` for stock bookings and order receipts (SEC-09).
 *
 * The same request (method, path, body) reuses its key until the server gave a
 * definite answer. A retry after a timeout, a lost connection or a double click
 * therefore cannot book twice; the server replays the first result. After
 * success or a definite rejection (4xx) the next identical request is a new
 * booking with a new key. Keys live only in memory.
 */
const openKeys = new Map<string, string>()

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([, item]) => item !== undefined)
      .sort(([a], [b]) => a.localeCompare(b))
    return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${stableStringify(item)}`).join(',')}}`
  }
  return JSON.stringify(value) ?? 'null'
}

function newKey(): string {
  // randomUUID needs a secure context; getRandomValues works everywhere.
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  return Array.from(bytes, (byte: number) => byte.toString(16).padStart(2, '0')).join('')
}

function isDefinite(error: unknown): boolean {
  const status = (error as AxiosError).response?.status
  return status !== undefined && status >= 400 && status < 500
}

export async function withIdempotencyKey<T>(
  method: string,
  url: string,
  data: unknown,
  send: (headers: { 'Idempotency-Key': string }) => Promise<T>,
): Promise<T> {
  const fingerprint = `${method.toUpperCase()} ${url} ${stableStringify(data)}`
  let key = openKeys.get(fingerprint)
  if (!key) {
    key = newKey()
    openKeys.set(fingerprint, key)
  }
  try {
    const result = await send({ 'Idempotency-Key': key })
    openKeys.delete(fingerprint)
    return result
  } catch (error) {
    // Unknown outcome (network, timeout, 5xx): keep the key for a safe retry.
    if (isDefinite(error)) openKeys.delete(fingerprint)
    throw error
  }
}

/** Test helper: forget every open key. */
export function resetIdempotencyKeys(): void {
  openKeys.clear()
}
