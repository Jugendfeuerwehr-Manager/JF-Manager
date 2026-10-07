import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'

const { mfaStatus, reauthenticate, reauthPasskeyOptions, getPasskeyAssertion, supported } = vi.hoisted(() => ({
  mfaStatus: vi.fn(), reauthenticate: vi.fn(), reauthPasskeyOptions: vi.fn(), getPasskeyAssertion: vi.fn(),
  supported: { value: true },
}))
vi.mock('@/api/auth', () => ({ authApi: { mfaStatus, reauthenticate, reauthPasskeyOptions } }))
vi.mock('@/utils/webauthn', () => ({
  getPasskeyAssertion,
  passkeysSupported: () => supported.value,
  passkeyErrorMessage: (err: { name?: string }) => (err?.name === 'NotAllowedError' ? 'abgebrochen' : null),
}))

import { confirmStepUpWithPasskey, requestStepUp, stepUpState } from '../useStepUp'

const status = (totp: boolean, passkeys: number) => ({
  data: { enabled: totp || passkeys > 0, totp_enabled: totp, passkeys: Array.from({ length: passkeys }, (_, id) => ({ id })) },
})

describe('step-up with passkeys', () => {
  beforeEach(() => { vi.clearAllMocks(); supported.value = true })

  it('passkey-only accounts confirm with the passkey and may fall back to a code', async () => {
    mfaStatus.mockResolvedValue(status(false, 1))
    const result = requestStepUp(true)
    await flushPromises()
    expect(stepUpState.passkeyAvailable).toBe(true)
    expect(stepUpState.needsCode).toBe(false)
    expect(stepUpState.codeOptional).toBe(true)
    expect(stepUpState.ssoOnly).toBe(false)

    reauthPasskeyOptions.mockResolvedValue({ data: { challenge: 'AQID' } })
    getPasskeyAssertion.mockResolvedValue({ id: 'assertion' })
    reauthenticate.mockResolvedValue({ data: { reauthenticated: true } })
    await confirmStepUpWithPasskey('secret')
    expect(reauthenticate).toHaveBeenCalledWith({ password: 'secret', passkey: { id: 'assertion' } })
    await expect(result).resolves.toBe(true)
  })

  it('accounts with an authenticator app still need the code field', async () => {
    mfaStatus.mockResolvedValue(status(true, 1))
    void requestStepUp(true)
    await flushPromises()
    expect(stepUpState.needsCode).toBe(true)
    expect(stepUpState.passkeyAvailable).toBe(true)
  })

  it('without browser support a passkey account confirms with a recovery code', async () => {
    supported.value = false
    mfaStatus.mockResolvedValue(status(false, 1))
    void requestStepUp(true)
    await flushPromises()
    expect(stepUpState.passkeyAvailable).toBe(false)
    expect(stepUpState.needsCode).toBe(true)
  })

  it('a cancelled passkey keeps the dialog open with a message', async () => {
    mfaStatus.mockResolvedValue(status(false, 1))
    void requestStepUp(true)
    await flushPromises()
    reauthPasskeyOptions.mockResolvedValue({ data: {} })
    getPasskeyAssertion.mockRejectedValue({ name: 'NotAllowedError' })
    await confirmStepUpWithPasskey('secret')
    expect(stepUpState.visible).toBe(true)
    expect(stepUpState.error).toBe('abgebrochen')
    expect(reauthenticate).not.toHaveBeenCalled()
  })
})
