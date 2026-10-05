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
  (error: AxiosError<{ code?: string }>) => {
    const status = error.response?.status
    const url = error.config?.url ?? ''
    // Login, MFA and status calls report their own outcome to the caller.
    if (status === 401 && !url.startsWith('/auth/session')) {
      sessionListeners.forEach(listener => listener('expired'))
    } else if (status === 403 && error.response?.data?.code === 'mfa_setup_required') {
      sessionListeners.forEach(listener => listener('mfa_setup_required'))
    }
    return Promise.reject(error)
  }
)

export default apiClient
