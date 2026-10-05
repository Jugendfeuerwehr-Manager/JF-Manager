import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AxiosError, AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'
import { resetIdempotencyKeys, withIdempotencyKey } from '../idempotency'

function failure(status?: number) {
  const config = { headers: new AxiosHeaders() } as InternalAxiosRequestConfig
  return new AxiosError('failed', 'ERR', config, undefined, status === undefined ? undefined : {
    status, statusText: '', data: {}, headers: new AxiosHeaders(), config,
  })
}

describe('withIdempotencyKey', () => {
  beforeEach(() => resetIdempotencyKeys())

  it('reuses the key after an unknown outcome so a retry cannot book twice', async () => {
    const send = vi.fn().mockRejectedValueOnce(failure()).mockResolvedValueOnce('booked')
    await expect(withIdempotencyKey('post', '/inventory/transactions/', { quantity: 1, item: 2 }, send)).rejects.toThrow()
    await withIdempotencyKey('post', '/inventory/transactions/', { item: 2, quantity: 1 }, send)
    expect(send.mock.calls[0]![0]['Idempotency-Key']).toBe(send.mock.calls[1]![0]['Idempotency-Key'])
  })

  it('starts a new booking after success or a definite rejection', async () => {
    const keys: string[] = []
    const send = vi.fn(async (headers: { 'Idempotency-Key': string }) => { keys.push(headers['Idempotency-Key']) })
    await withIdempotencyKey('post', '/x/', { a: 1 }, send)
    await withIdempotencyKey('post', '/x/', { a: 1 }, send)
    const rejected = vi.fn(async (headers: { 'Idempotency-Key': string }) => { keys.push(headers['Idempotency-Key']); throw failure(400) })
    await expect(withIdempotencyKey('post', '/x/', { a: 1 }, rejected)).rejects.toThrow()
    await withIdempotencyKey('post', '/x/', { a: 1 }, send)
    expect(new Set(keys).size).toBe(4)
  })

  it('shares one key between concurrent identical submissions', async () => {
    const releases: (() => void)[] = []
    const send = vi.fn((_headers: { 'Idempotency-Key': string }) => new Promise<void>(resolve => { releases.push(resolve) }))
    const first = withIdempotencyKey('post', '/x/', { a: 1 }, send)
    const second = withIdempotencyKey('post', '/x/', { a: 1 }, send)
    releases.forEach(release => release())
    await Promise.all([first, second])
    expect(send.mock.calls[0]![0]['Idempotency-Key']).toBe(send.mock.calls[1]![0]['Idempotency-Key'])
  })

  it('uses different keys for different content', async () => {
    const send = vi.fn().mockRejectedValue(failure(503))
    await expect(withIdempotencyKey('post', '/x/', { a: 1 }, send)).rejects.toThrow()
    await expect(withIdempotencyKey('post', '/x/', { a: 2 }, send)).rejects.toThrow()
    expect(send.mock.calls[0]![0]['Idempotency-Key']).not.toBe(send.mock.calls[1]![0]['Idempotency-Key'])
  })
})
