import { describe, expect, it } from 'vitest'
import {
  base64urlToBuffer,
  bufferToBase64url,
  creationOptionsFromJson,
  credentialToJson,
  passkeyErrorMessage,
  requestOptionsFromJson,
} from '../webauthn'

const bytes = (...values: number[]) => new Uint8Array(values).buffer

describe('webauthn helpers', () => {
  it('round-trips base64url without padding', () => {
    const data = bytes(0xfb, 0xff, 0x00, 0x10)
    const encoded = bufferToBase64url(data)
    expect(encoded).toBe('-_8AEA')
    expect(new Uint8Array(base64urlToBuffer(encoded))).toEqual(new Uint8Array(data))
  })

  it('decodes challenge, user id and excluded credentials for create()', () => {
    const options = creationOptionsFromJson({
      challenge: 'AQID',
      rp: { id: 'jf.example.org', name: 'JF-Manager' },
      user: { id: 'BAU', name: 'jugendleitung', displayName: 'Jugendleitung' },
      pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
      excludeCredentials: [{ id: 'Bwg', type: 'public-key', transports: ['internal'] }],
    })
    expect(new Uint8Array(options.challenge as ArrayBuffer)).toEqual(new Uint8Array([1, 2, 3]))
    expect(new Uint8Array(options.user.id as ArrayBuffer)).toEqual(new Uint8Array([4, 5]))
    expect(new Uint8Array(options.excludeCredentials![0]!.id as ArrayBuffer)).toEqual(new Uint8Array([7, 8]))
    expect(options.rp.id).toBe('jf.example.org')
  })

  it('decodes allowed credentials for get()', () => {
    const options = requestOptionsFromJson({ challenge: 'AQID', rpId: 'jf.example.org', allowCredentials: [{ id: 'CQ', type: 'public-key' }] })
    expect(new Uint8Array(options.allowCredentials![0]!.id as ArrayBuffer)).toEqual(new Uint8Array([9]))
  })

  it('serialises registration and assertion responses for the server', () => {
    const registration = credentialToJson({
      id: 'Bwg', rawId: bytes(7, 8), type: 'public-key', getClientExtensionResults: () => ({}),
      response: { clientDataJSON: bytes(1), attestationObject: bytes(2), getTransports: () => ['internal'] },
    } as unknown as PublicKeyCredential)
    expect(registration).toMatchObject({ rawId: 'Bwg', response: { clientDataJSON: 'AQ', attestationObject: 'Ag', transports: ['internal'] } })

    const assertion = credentialToJson({
      id: 'Bwg', rawId: bytes(7, 8), type: 'public-key', getClientExtensionResults: () => ({}),
      response: { clientDataJSON: bytes(1), authenticatorData: bytes(3), signature: bytes(4), userHandle: null },
    } as unknown as PublicKeyCredential)
    expect(assertion).toMatchObject({ response: { authenticatorData: 'Aw', signature: 'BA', userHandle: null } })
  })

  it('explains browser-side failures', () => {
    expect(passkeyErrorMessage({ name: 'NotAllowedError' })).toContain('abgebrochen')
    expect(passkeyErrorMessage({ name: 'SecurityError' })).toContain('HTTPS')
    expect(passkeyErrorMessage(new Error('other'))).toBeNull()
  })
})
