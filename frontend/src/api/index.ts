import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

/**
 * Browser sessions use an HttpOnly cookie set by the backend; the SPA never
 * sees an access token. Frontend and API must share one origin so the CSRF
 * cookie can be returned as header (axios does this for same-origin requests).
 */
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

export type SessionProblem = 'expired' | 'mfa_setup_required'
type SessionProblemListener = (problem: SessionProblem) => void
const sessionListeners = new Set<SessionProblemListener>()

/** The auth store subscribes here; avoids an import cycle with Pinia. */
export function onSessionProblem(listener: SessionProblemListener): () => void {
  sessionListeners.add(listener)
  return () => sessionListeners.delete(listener)
}

type StepUpHandler = () => Promise<boolean>
let stepUpHandler: StepUpHandler | null = null
let pendingStepUp: Promise<boolean> | null = null

/**
 * Registered by the global confirmation dialog. Actions that widen access answer
 * 403 `reauthentication_required`; after a successful confirmation the request
 * is sent once more.
 */
export function setStepUpHandler(handler: StepUpHandler | null): void {
  stepUpHandler = handler
}

function blobText(blob: Blob): Promise<string> {
  if (typeof blob.text === 'function') return blob.text()
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(reader.error)
    reader.readAsText(blob)
  })
}

async function errorCode(data: unknown): Promise<string | undefined> {
  // Download requests receive their error body as Blob.
  if (typeof Blob !== 'undefined' && data instanceof Blob) {
    try {
      return (JSON.parse(await blobText(data)) as { code?: string }).code
    } catch {
      return undefined
    }
  }
  return (data as { code?: string } | undefined)?.code
}

// Request interceptor - add the active department filter.
//
// The active department is intentionally attached to most GET requests so the
// backend can resolve department-scoped permissions and default context.
// Endpoints that expose central/shared records must therefore treat this query
// parameter as an active-context hint, not as a hard exclusion of department=NULL.
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Inject active department as query param for scoped list endpoints.
    // Only inject on GET requests to avoid interfering with write operations.
    // Skip the /departments/ endpoint itself and /admin/ routes.
    const activeDeptId = localStorage.getItem('activeDepartmentId')
    if (
      activeDeptId &&
      config.method?.toLowerCase() === 'get' &&
      config.url &&
      !config.url.startsWith('/departments') &&
      !config.url.startsWith('/admin/') &&
      !config.url.startsWith('/auth/')
    ) {
      config.params = {
        ...config.params,
        // An explicit department is a deliberate target/filter from the caller.
        ...(config.params?.department == null ? { department: activeDeptId } : {}),
      }
    }

    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const status = error.response?.status
    const config = error.config as (InternalAxiosRequestConfig & { _stepUpRetried?: boolean }) | undefined
    const url = config?.url ?? ''
    // Login, MFA and status calls report their own outcome to the caller.
    if (status === 401 && !url.startsWith('/auth/session')) {
      sessionListeners.forEach(listener => listener('expired'))
    } else if (status === 403) {
      const code = await errorCode(error.response?.data)
      if (code === 'mfa_setup_required') {
        sessionListeners.forEach(listener => listener('mfa_setup_required'))
      } else if (code === 'reauthentication_required' && stepUpHandler && config && !config._stepUpRetried) {
        // Parallel requests share one confirmation dialog.
        pendingStepUp ??= stepUpHandler().finally(() => { pendingStepUp = null })
        if (await pendingStepUp) {
          config._stepUpRetried = true
          return apiClient(config)
        }
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
