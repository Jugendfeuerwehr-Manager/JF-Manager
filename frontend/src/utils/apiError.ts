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
    }
  }
  message?: string
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  const e = error as ApiErrorShape
  return e.response?.data?.detail ?? e.message ?? fallback
}
