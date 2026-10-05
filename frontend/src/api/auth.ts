import apiClient from './index'
import type { LoginRequest } from '@/types/api'

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
  /** Signed in, but the account must set up MFA before using the app. */
  mfa_setup_required?: boolean
  idle_expires_at?: string
  absolute_expires_at?: string
  idle_timeout_seconds?: number
  /** Short session profile for accounts with mandatory MFA. */
  privileged_session?: boolean
}

export interface MFAStatus {
  enabled: boolean
  setup_pending: boolean
  recovery_codes_remaining: number
  required: boolean
}

export interface MFASetup {
  secret: string
  otpauth_uri: string
}

export interface ReauthenticateRequest {
  password?: string
  code?: string
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
