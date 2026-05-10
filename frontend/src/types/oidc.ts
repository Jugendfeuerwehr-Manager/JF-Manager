/**
 * OIDC / SSO Types
 * TypeScript interfaces for OpenID Connect authentication
 */

// ============================================================================
// Public config (shown on login page — no secrets)
// ============================================================================

export interface OIDCPublicConfig {
  enabled: boolean
  provider_name: string
  hide_local_login: boolean
}

// ============================================================================
// Login flow
// ============================================================================

export interface OIDCLoginResponse {
  authorization_url: string
}

export interface OIDCExchangeRequest {
  exchange_code: string
}

export interface OIDCTokenResponse {
  access: string
  refresh: string
  next: string
}

// ============================================================================
// Settings (admin UI)
// ============================================================================

export interface OIDCSettings {
  enabled: boolean
  provider_name: string
  issuer_url: string
  client_id: string
  client_secret?: string  // write-only
  has_client_secret: boolean
  callback_url?: string  // read-only, computed by backend from request
  scope: string
  groups_claim: string
  staff_group: string
  admin_group: string
  require_group_mapping: boolean
  hide_local_login: boolean
}

// ============================================================================
// Group mappings
// ============================================================================

export interface OIDCGroupMapping {
  id: number
  group_claim_value: string
  department: number | null
  department_name: string
  auth_groups: { id: number; name: string }[]
  auth_group_ids: number[]
  revoke_on_mismatch: boolean
}

export interface OIDCGroupMappingCreate {
  group_claim_value: string
  department?: number | null
  auth_group_ids?: number[]
  revoke_on_mismatch?: boolean
}

// ============================================================================
// Discovery test result
// ============================================================================

export interface OIDCDiscoveryResult {
  ok: boolean
  detail?: string
  issuer?: string
  authorization_endpoint?: string
  token_endpoint?: string
  userinfo_endpoint?: string
  jwks_uri?: string
  scopes_supported?: string[]
  claims_supported?: string[]
}
