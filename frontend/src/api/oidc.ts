/**
 * OIDC API client
 * All calls to the OIDC authentication endpoints. The login flow is bound to
 * the browser session cookie, so it uses the shared same-origin client.
 */
import apiClient from './index'
import type {
  OIDCDiscoveryResult,
  OIDCGroupMapping,
  OIDCGroupMappingCreate,
  OIDCLoginResponse,
  OIDCPublicConfig,
  OIDCSettings,
} from '@/types/oidc'

export const oidcApi = {
  /**
   * Fetch the public OIDC config (enabled, provider_name, hide_local_login).
   * Called on the login page without auth.
   */
  getPublicConfig() {
    return apiClient.get<OIDCPublicConfig>('/auth/oidc/public-config/')
  },

  /**
   * Get the authorization URL to redirect the user to the IdP.
   * State, nonce and PKCE verifier are stored in this browser's session.
   */
  getLoginUrl(next?: string) {
    const params = next ? { next } : undefined
    return apiClient.get<OIDCLoginResponse>('/auth/oidc/login/', { params })
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
