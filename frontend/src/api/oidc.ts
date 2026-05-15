/**
 * OIDC API client
 * All calls to the OIDC authentication endpoints.
 *
 * Note: public-config and login/callback are called without auth headers.
 * We use a plain axios instance for those to avoid accidental token injection.
 */
import axios from 'axios'
import apiClient from './index'
import type {
  OIDCDiscoveryResult,
  OIDCExchangeRequest,
  OIDCGroupMapping,
  OIDCGroupMappingCreate,
  OIDCLoginResponse,
  OIDCPublicConfig,
  OIDCSettings,
  OIDCTokenResponse,
} from '@/types/oidc'

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

// Unauthenticated client for public OIDC endpoints
const publicClient = axios.create({
  baseURL: BASE,
  headers: { 'Content-Type': 'application/json' },
})

export const oidcApi = {
  /**
   * Fetch the public OIDC config (enabled, provider_name, hide_local_login).
   * Called on the login page without auth.
   */
  getPublicConfig() {
    return publicClient.get<OIDCPublicConfig>('/auth/oidc/public-config/')
  },

  /**
   * Get the authorization URL to redirect the user to the IdP.
   * The backend returns a URL with state + nonce already embedded.
   */
  getLoginUrl(next?: string) {
    const params = next ? { next } : undefined
    return publicClient.get<OIDCLoginResponse>('/auth/oidc/login/', { params })
  },

  /**
   * Exchange a one-time exchange_code (from the callback query param) for JWT tokens.
   * Called by OIDCCallbackView.vue immediately after redirect from IdP.
   */
  exchangeCode(data: OIDCExchangeRequest) {
    return publicClient.post<OIDCTokenResponse>('/auth/oidc/exchange/', data)
  },

  // -------------------------------------------------------------------------
  // Settings API (requires auth + change_oidc_settings permission)
  // -------------------------------------------------------------------------

  getSettings() {
    return apiClient.get<OIDCSettings>('/settings/oidc/')
  },

  updateSettings(data: Partial<OIDCSettings>) {
    return apiClient.patch<OIDCSettings>('/settings/oidc/', data)
  },

  testDiscovery(issuerUrl: string) {
    return apiClient.post<OIDCDiscoveryResult>('/settings/oidc/test-discovery/', {
      issuer_url: issuerUrl,
    })
  },

  // -------------------------------------------------------------------------
  // Group mappings
  // -------------------------------------------------------------------------

  listGroupMappings() {
    return apiClient.get<OIDCGroupMapping[]>('/oidc-group-mappings/')
  },

  createGroupMapping(data: OIDCGroupMappingCreate) {
    return apiClient.post<OIDCGroupMapping>('/oidc-group-mappings/', data)
  },

  deleteGroupMapping(id: number) {
    return apiClient.delete(`/oidc-group-mappings/${id}/`)
  },
}
