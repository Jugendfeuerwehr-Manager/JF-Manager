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
