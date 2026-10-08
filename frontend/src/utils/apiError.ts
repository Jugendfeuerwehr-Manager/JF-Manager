/**
 * Utility for extracting human-readable error messages from API errors.
 *
 * Usage in catch blocks:
 *   } catch (err) {
 *     someError.value = getApiErrorMessage(err, 'Fallback message')
 *   }
 */

type ApiErrorShape = {
  response?: {
    data?: {
      detail?: string
      [key: string]: unknown
    }
  }
  message?: string
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  const e = error as ApiErrorShape
  const data = e.response?.data
  if (data?.detail) return data.detail
  if (data) {
    for (const value of Object.values(data)) {
      if (typeof value === 'string') return value
      if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
    }
  }
  return e.message ?? fallback
}

export type ApiErrorKind = 'forbidden' | 'unauthorized' | 'not_found' | 'conflict' | 'validation' | 'network' | 'server'

/**
 * Sorts an API error into the states the UI distinguishes, so a missing
 * permission or a lost connection is never shown as "no data".
 */
export function classifyApiError(error: unknown): ApiErrorKind {
  const e = error as { response?: { status?: number }; code?: string }
  const status = e.response?.status
  if (status === undefined) return 'network'
  if (status === 401) return 'unauthorized'
  if (status === 403) return 'forbidden'
  if (status === 404) return 'not_found'
  if (status === 409 || status === 412) return 'conflict'
  if (status >= 400 && status < 500) return 'validation'
  return 'server'
}
