import { useRoute, useRouter } from 'vue-router'

/**
 * Composable for persisting table state (filters, pagination, sorting) in the URL.
 * Uses router.replace so navigation state is preserved without polluting history.
 */
export function useQueryTableState() {
  const route = useRoute()
  const router = useRouter()

  /** Read an integer query param, returning defaultVal if absent or invalid. */
  function getInt(key: string, defaultVal: number): number {
    const val = route.query[key]
    if (val === undefined || val === null || val === '') return defaultVal
    const num = Number(val)
    return isNaN(num) ? defaultVal : num
  }

  /** Read a string query param, returning defaultVal if absent. */
  function getString(key: string, defaultVal = ''): string {
    const val = route.query[key]
    return val !== undefined && val !== null && val !== '' ? String(val) : defaultVal
  }

  /**
   * Replace the current URL query with the given params.
   * Params equal to their default value (provided in `defaults`) are omitted to keep URLs clean.
   * Null/undefined/empty-string values are always omitted.
   */
  function syncToUrl(
    params: Record<string, string | number | null | undefined>,
    defaults: Record<string, string | number> = {}
  ): void {
    const query: Record<string, string> = {}
    for (const [key, value] of Object.entries(params)) {
      if (value === null || value === undefined || value === '') continue
      if (key in defaults && defaults[key] === value) continue
      query[key] = String(value)
    }
    router.replace({ query })
  }

  return { getInt, getString, syncToUrl }
}
