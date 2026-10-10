import { beforeEach, describe, expect, it, vi } from 'vitest'

const { post } = vi.hoisted(() => ({ post: vi.fn() }))
vi.mock('../index', () => ({ default: { post } }))

import { emailsApi } from '../emails'
import { resetIdempotencyKeys } from '../idempotency'

describe('emailsApi.send (UX-07.2)', () => {
  beforeEach(() => {
    post.mockReset()
    resetIdempotencyKeys()
  })

  it('sends with an idempotency key and reuses it when the request is retried', async () => {
    post.mockRejectedValueOnce(new Error('Network Error')).mockResolvedValueOnce({ data: { result: null, queued: true } })
    const data = { subject: 'Info', body_html: '<p>Hi</p>', body_text: 'Hi', recipient_type: 'all' as const }
    await expect(emailsApi.send(data)).rejects.toThrow('Network Error')
    await emailsApi.send(data)
    const keys = post.mock.calls.map((call) => call[2].headers['Idempotency-Key'])
    expect(keys[0]).toBeTruthy()
    expect(keys[1]).toBe(keys[0])
  })
})
