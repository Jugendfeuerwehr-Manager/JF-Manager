import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

// Create axios instance
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor - Add auth token and active department filter.
//
// The active department is intentionally attached to most GET requests so the
// backend can resolve department-scoped permissions and default context.
// Endpoints that expose central/shared records must therefore treat this query
// parameter as an active-context hint, not as a hard exclusion of department=NULL.
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get token from localStorage directly to avoid Pinia initialization issues
    const token = localStorage.getItem('accessToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Inject active department as query param for scoped list endpoints.
    // Only inject on GET requests to avoid interfering with write operations.
    // Skip the /departments/ endpoint itself and /admin/ routes.
    const activeDeptId = localStorage.getItem('activeDepartmentId')
    if (
      activeDeptId &&
      config.method?.toLowerCase() === 'get' &&
      config.url &&
      !config.url.startsWith('/departments') &&
      !config.url.startsWith('/admin/')
    ) {
      config.params = { ...config.params, department: activeDeptId }
    }

    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// Share a refresh operation so concurrent requests do not reuse a rotated token.
let refreshPromise: Promise<string> | null = null

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
    if (
      error.response?.status !== 401 || !originalRequest || originalRequest._retry ||
      originalRequest.url?.startsWith('/auth/')
    ) return Promise.reject(error)

    originalRequest._retry = true
    const refreshToken = localStorage.getItem('refreshToken')
    if (!refreshToken) return Promise.reject(error)

    try {
      const currentAccess = localStorage.getItem('accessToken')
      // A different request may already have completed the refresh.
      if (currentAccess && originalRequest.headers.Authorization !== `Bearer ${currentAccess}`) {
        originalRequest.headers.Authorization = `Bearer ${currentAccess}`
        return apiClient(originalRequest)
      }
      if (!refreshPromise) {
        refreshPromise = axios.post(`${apiClient.defaults.baseURL}/auth/refresh/`, { refresh: refreshToken })
          .then((response) => {
            // Logout or a different login must not be undone by an in-flight response.
            if (localStorage.getItem('refreshToken') !== refreshToken) {
              throw new Error('Anmeldung wurde zwischenzeitlich geändert.')
            }
            localStorage.setItem('accessToken', response.data.access)
            if (response.data.refresh) localStorage.setItem('refreshToken', response.data.refresh)
            return response.data.access as string
          })
          .finally(() => { refreshPromise = null })
      }
      originalRequest.headers.Authorization = `Bearer ${await refreshPromise}`
      return apiClient(originalRequest)
    } catch (refreshError) {
      if (localStorage.getItem('refreshToken') === refreshToken) {
        localStorage.removeItem('accessToken')
        localStorage.removeItem('refreshToken')
        window.location.href = '/login'
      }
      return Promise.reject(refreshError)
    }
  }
)

export default apiClient
