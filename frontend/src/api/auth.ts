import apiClient from './index'
import type { LoginRequest } from '@/types/api'
import type { JsonObject } from '@/utils/webauthn'

export interface PasswordResetRequest {
  email: string
}

export interface PasswordResetConfirm {
  token: string
  uid: string
  new_password: string
  new_password_confirm: string
}

export interface PasswordChange {
  old_password: string
  new_password: string
  new_password_confirm: string
}

export interface MessageResponse {
  message: string
}

export interface SessionStatus {
  authenticated: boolean
  /** Password (or SSO) accepted; the second factor is still missing. */
  mfa_required?: boolean
  /** Second factors of the pending login (only after a correct password). */
  mfa_methods?: { totp: boolean, passkey: boolean }
  /** Signed in, but the account must set up MFA before using the app. */
  mfa_setup_required?: boolean
  idle_expires_at?: string
  absolute_expires_at?: string
  idle_timeout_seconds?: number
  /** Short session profile for accounts with mandatory MFA. */
  privileged_session?: boolean
  account_kind?: 'staff' | 'portal'
  /** Staff account with a link waiting for its confirmation (PORTAL-04.2). */
  account_link_pending?: boolean
  /** Confirmed link: own member record and/or minor children of the own parent record. */
  linked_person?: { member: boolean, children: boolean }
  /** Own member record and own children: evidence is kept by another person (four-eyes). */
  own_member_ids?: number[]
}

export interface Passkey {
  id: number
  name: string
  created_at: string
  last_used_at: string | null
  backed_up: boolean
}

export interface MFAStatus {
  /** Any second factor: authenticator app or passkey. */
  enabled: boolean
  totp_enabled: boolean
  passkeys: Passkey[]
  setup_pending: boolean
  recovery_codes_remaining: number
  required: boolean
}

export interface MFASetup {
  secret: string
  otpauth_uri: string
}

export interface DeviceSession {
  id: number
  user_agent: string
  created_at: string
  last_seen_at: string
  current: boolean
}

export interface DeviceRevokeResult {
  revoked: number
  current: boolean
}

export interface ReauthenticateRequest {
  password?: string
  code?: string
  passkey?: JsonObject
}

export const authApi = {
  /** Also sets the CSRF cookie needed for all following writes. */
  session() {
    return apiClient.get<SessionStatus>('/auth/session/')
  },

  login(credentials: LoginRequest) {
    return apiClient.post<SessionStatus>('/auth/session/login/', credentials)
  },

  verifyMfa(code: string) {
    return apiClient.post<SessionStatus>('/auth/session/mfa/', { code })
  },

  loginPasskeyOptions() {
    return apiClient.post<JsonObject>('/auth/session/mfa/passkey-options/')
  },

  verifyMfaPasskey(passkey: JsonObject) {
    return apiClient.post<SessionStatus>('/auth/session/mfa/', { passkey })
  },

  /** Sign-in without password: the browser offers the stored passkeys (SEC-12). */
  passkeySignInOptions() {
    return apiClient.post<JsonObject>('/auth/session/passkey/options/')
  },

  passkeySignIn(passkey: JsonObject) {
    return apiClient.post<SessionStatus>('/auth/session/passkey/', { passkey })
  },

  reauthPasskeyOptions() {
    return apiClient.post<JsonObject>('/auth/reauthenticate/passkey-options/')
  },

  logout() {
    return apiClient.post<SessionStatus>('/auth/session/logout/')
  },

  reauthenticate(data: ReauthenticateRequest) {
    return apiClient.post<{ reauthenticated: boolean }>('/auth/reauthenticate/', data)
  },

  mfaStatus() {
    return apiClient.get<MFAStatus>('/auth/mfa/')
  },

  mfaSetup() {
    return apiClient.post<MFASetup>('/auth/mfa/setup/')
  },

  mfaConfirm(code: string) {
    return apiClient.post<MFAStatus & { recovery_codes: string[] }>('/auth/mfa/confirm/', { code })
  },

  mfaRecoveryCodes() {
    return apiClient.post<{ recovery_codes: string[] }>('/auth/mfa/recovery-codes/')
  },

  mfaDisable() {
    return apiClient.post<MFAStatus>('/auth/mfa/disable/')
  },

  mfaTotpRemove() {
    return apiClient.post<MFAStatus>('/auth/mfa/totp/remove/')
  },

  passkeyRegisterOptions() {
    return apiClient.post<JsonObject>('/auth/mfa/passkeys/register/begin/')
  },

  passkeyRegister(credential: JsonObject, name: string) {
    return apiClient.post<MFAStatus & { recovery_codes: string[] }>('/auth/mfa/passkeys/register/finish/', { credential, name })
  },

  passkeyRemove(id: number) {
    return apiClient.post<MFAStatus>(`/auth/mfa/passkeys/${id}/remove/`)
  },

  devices() {
    return apiClient.get<DeviceSession[]>('/auth/devices/')
  },

  revokeDevice(id: number) {
    return apiClient.post<DeviceRevokeResult>(`/auth/devices/${id}/revoke/`)
  },

  revokeOtherDevices() {
    return apiClient.post<DeviceRevokeResult>('/auth/devices/revoke-others/')
  },

  requestPasswordReset(email: string) {
    return apiClient.post<MessageResponse>('/users/request_password_reset/', { email })
  },

  resetPassword(data: PasswordResetConfirm) {
    return apiClient.post<MessageResponse>('/users/reset_password/', data)
  },

  changePassword(data: PasswordChange) {
    return apiClient.post<MessageResponse>('/users/change_password/', data)
  }
}
