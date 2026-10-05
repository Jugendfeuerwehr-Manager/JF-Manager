import { reactive } from 'vue'
import { authApi } from '@/api/auth'
import { getApiErrorMessage } from '@/utils/apiError'

/** Shared state of the single global step-up confirmation dialog. */
export const stepUpState = reactive({
  visible: false,
  busy: false,
  needsPassword: true,
  needsCode: false,
  ssoOnly: false,
  error: '',
})

let resolveRequest: ((confirmed: boolean) => void) | null = null

/** Opens the dialog; resolves true once the server accepted the confirmation. */
export async function requestStepUp(usesPassword: boolean): Promise<boolean> {
  let needsCode = false
  try {
    needsCode = (await authApi.mfaStatus()).data.enabled
  } catch {
    // Without status the server still decides; ask for the password only.
  }
  Object.assign(stepUpState, {
    visible: true,
    busy: false,
    needsPassword: usesPassword,
    needsCode,
    ssoOnly: !usesPassword && !needsCode,
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

export function cancelStepUp() {
  finish(false)
}
