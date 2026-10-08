import { reactive } from 'vue'
import { authApi } from '@/api/auth'
import { getApiErrorMessage } from '@/utils/apiError'
import { getPasskeyAssertion, passkeyErrorMessage, passkeysSupported } from '@/utils/webauthn'

/** Shared state of the single global step-up confirmation dialog. */
export const stepUpState = reactive({
  visible: false,
  busy: false,
  needsPassword: true,
  needsCode: false,
  /** The account has passkeys and this browser can use them (SEC-11). */
  passkeyAvailable: false,
  /** Passkey-only accounts may fall back to a recovery code. */
  codeOptional: false,
  ssoOnly: false,
  error: '',
})

let resolveRequest: ((confirmed: boolean) => void) | null = null

/** Opens the dialog; resolves true once the server accepted the confirmation. */
export async function requestStepUp(usesPassword: boolean): Promise<boolean> {
  let needsCode = false
  let passkeyAvailable = false
  let codeOptional = false
  try {
    const status = (await authApi.mfaStatus()).data
    passkeyAvailable = status.passkeys.length > 0 && passkeysSupported()
    // Passkey-only accounts confirm with the key; the code field is a fallback.
    needsCode = status.totp_enabled || (status.enabled && !passkeyAvailable)
    codeOptional = status.enabled && !status.totp_enabled && passkeyAvailable
  } catch {
    // Without status the server still decides; ask for the password only.
  }
  Object.assign(stepUpState, {
    visible: true,
    busy: false,
    needsPassword: usesPassword,
    needsCode,
    passkeyAvailable,
    codeOptional,
    ssoOnly: !usesPassword && !needsCode && !passkeyAvailable && !codeOptional,
    error: '',
  })
  return new Promise<boolean>(resolve => { resolveRequest = resolve })
}

function finish(confirmed: boolean) {
  stepUpState.visible = false
  resolveRequest?.(confirmed)
  resolveRequest = null
}

export async function confirmStepUp(password: string, code: string) {
  stepUpState.busy = true
  stepUpState.error = ''
  try {
    await authApi.reauthenticate({
      password: stepUpState.needsPassword ? password : undefined,
      code: stepUpState.needsCode ? code.trim() : undefined,
    })
    finish(true)
  } catch (err) {
    stepUpState.error = getApiErrorMessage(err, 'Bestätigung fehlgeschlagen.')
  } finally {
    stepUpState.busy = false
  }
}

export async function confirmStepUpWithPasskey(password: string) {
  stepUpState.busy = true
  stepUpState.error = ''
  try {
    const options = (await authApi.reauthPasskeyOptions()).data
    const passkey = await getPasskeyAssertion(options)
    await authApi.reauthenticate({ password: stepUpState.needsPassword ? password : undefined, passkey })
    finish(true)
  } catch (err) {
    stepUpState.error = passkeyErrorMessage(err) ?? getApiErrorMessage(err, 'Bestätigung fehlgeschlagen.')
  } finally {
    stepUpState.busy = false
  }
}

export function cancelStepUp() {
  finish(false)
}
