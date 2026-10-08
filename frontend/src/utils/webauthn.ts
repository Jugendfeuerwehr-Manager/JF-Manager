/**
 * Passkeys (WebAuthn) without extra dependencies: converts the server's JSON
 * options (base64url fields) into browser structures and back (SEC-11).
 */

export type JsonObject = Record<string, unknown>

export function base64urlToBuffer(value: string): ArrayBuffer {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/')
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes.buffer
}

export function bufferToBase64url(buffer: ArrayBuffer | ArrayBufferView): string {
  const bytes = buffer instanceof ArrayBuffer ? new Uint8Array(buffer) : new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength)
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

interface DescriptorJson { id: string, type: string, transports?: string[] }

function descriptors(list: unknown): PublicKeyCredentialDescriptor[] | undefined {
  if (!Array.isArray(list)) return undefined
  return (list as DescriptorJson[]).map(item => ({
    type: 'public-key',
    id: base64urlToBuffer(item.id),
    transports: item.transports as AuthenticatorTransport[] | undefined,
  }))
}

export function creationOptionsFromJson(options: JsonObject): PublicKeyCredentialCreationOptions {
  const user = options.user as { id: string, name: string, displayName: string }
  return {
    ...(options as unknown as PublicKeyCredentialCreationOptions),
    challenge: base64urlToBuffer(options.challenge as string),
    user: { ...user, id: base64urlToBuffer(user.id) },
    excludeCredentials: descriptors(options.excludeCredentials),
  }
}

export function requestOptionsFromJson(options: JsonObject): PublicKeyCredentialRequestOptions {
  return {
    ...(options as unknown as PublicKeyCredentialRequestOptions),
    challenge: base64urlToBuffer(options.challenge as string),
    allowCredentials: descriptors(options.allowCredentials),
  }
}

export function credentialToJson(credential: PublicKeyCredential): JsonObject {
  const response = credential.response as AuthenticatorAttestationResponse & AuthenticatorAssertionResponse
  const json: JsonObject = {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    clientExtensionResults: credential.getClientExtensionResults?.() ?? {},
  }
  if ('attestationObject' in response && response.attestationObject) {
    json.response = {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      attestationObject: bufferToBase64url(response.attestationObject),
      transports: typeof response.getTransports === 'function' ? response.getTransports() : [],
    }
  } else {
    json.response = {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      authenticatorData: bufferToBase64url(response.authenticatorData),
      signature: bufferToBase64url(response.signature),
      userHandle: response.userHandle ? bufferToBase64url(response.userHandle) : null,
    }
  }
  return json
}

export function passkeysSupported(): boolean {
  return typeof window !== 'undefined' && typeof window.PublicKeyCredential !== 'undefined' && !!navigator.credentials
}

/** User-facing message for browser-side failures (cancelled, timeout, wrong device). */
export function passkeyErrorMessage(err: unknown): string | null {
  const name = (err as { name?: string })?.name
  if (name === 'NotAllowedError' || name === 'AbortError') return 'Der Passkey-Vorgang wurde abgebrochen oder ist abgelaufen.'
  if (name === 'InvalidStateError') return 'Dieser Passkey ist für dein Konto bereits registriert.'
  if (name === 'SecurityError') return 'Passkeys funktionieren nur über HTTPS unter der Adresse der Anwendung.'
  if (name === 'NotSupportedError') return 'Dieser Browser unterstützt keine Passkeys.'
  return null
}

export async function createPasskey(options: JsonObject): Promise<JsonObject> {
  const credential = await navigator.credentials.create({ publicKey: creationOptionsFromJson(options) })
  if (!credential) throw Object.assign(new Error('cancelled'), { name: 'NotAllowedError' })
  return credentialToJson(credential as PublicKeyCredential)
}

export async function getPasskeyAssertion(options: JsonObject): Promise<JsonObject> {
  const credential = await navigator.credentials.get({ publicKey: requestOptionsFromJson(options) })
  if (!credential) throw Object.assign(new Error('cancelled'), { name: 'NotAllowedError' })
  return credentialToJson(credential as PublicKeyCredential)
}
