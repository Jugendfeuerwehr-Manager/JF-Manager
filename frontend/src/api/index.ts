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

// Response interceptor - Handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // If 401 and not already retried, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = localStorage.getItem('refreshToken')
      if (refreshToken) {
        try {
          // Try to refresh the token
          const response = await axios.post(
            `${apiClient.defaults.baseURL}/auth/refresh/`,
            { refresh: refreshToken }
          )
          
          const newAccessToken = response.data.access
          localStorage.setItem('accessToken', newAccessToken)

          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
          }
          return apiClient(originalRequest)
        } catch (refreshError) {
          // Refresh failed, clear storage and redirect to login
          localStorage.removeItem('accessToken')
          localStorage.removeItem('refreshToken')
          window.location.href = '/login'
          return Promise.reject(refreshError)
        }
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
