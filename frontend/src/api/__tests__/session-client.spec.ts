import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AxiosError, AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'

function failing(status: number, data: Record<string, unknown> = {}) {
  return async (config: InternalAxiosRequestConfig) => {
    throw new AxiosError('Failed', 'ERR_BAD_REQUEST', config, undefined, {
      status, statusText: 'Error', data, headers: new AxiosHeaders(), config
    })
  }
}

describe('session API client', () => {
  beforeEach(() => {
    vi.resetModules()
    localStorage.clear()
  })

  it('sends cookies and the CSRF header instead of bearer tokens', async () => {
    localStorage.setItem('accessToken', 'legacy-token')
    const { default: client } = await import('../index')
    let seen: InternalAxiosRequestConfig | undefined
    client.defaults.adapter = async config => {
      seen = config
      return { status: 200, statusText: 'OK', data: {}, headers: new AxiosHeaders(), config }
    }
    await client.post('/members/', {})
    expect(seen?.withCredentials).toBe(true)
    expect(seen?.xsrfCookieName).toBe('csrftoken')
    expect(seen?.xsrfHeaderName).toBe('X-CSRFToken')
    expect(seen?.headers.Authorization).toBeUndefined()
  })

  it('reports an expired session for API calls but not for the login itself', async () => {
    const { default: client, onSessionProblem } = await import('../index')
    const listener = vi.fn()
    onSessionProblem(listener)
    client.defaults.adapter = failing(401)
    await expect(client.post('/auth/session/login/', {})).rejects.toBeInstanceOf(AxiosError)
    expect(listener).not.toHaveBeenCalled()
    await expect(client.get('/members/')).rejects.toBeInstanceOf(AxiosError)
    expect(listener).toHaveBeenCalledWith('expired')
  })

  it('reports a mandatory MFA setup', async () => {
    const { default: client, onSessionProblem } = await import('../index')
    const listener = vi.fn()
    onSessionProblem(listener)
    client.defaults.adapter = failing(403, { code: 'mfa_setup_required' })
    await expect(client.get('/members/')).rejects.toBeInstanceOf(AxiosError)
    expect(listener).toHaveBeenCalledWith('mfa_setup_required')
  })

  it('asks once for step-up confirmation and repeats the request', async () => {
    const { default: client, setStepUpHandler } = await import('../index')
    const handler = vi.fn().mockResolvedValue(true)
    setStepUpHandler(handler)
    let calls = 0
    client.defaults.adapter = async config => {
      calls += 1
      if (calls === 1) return failing(403, { code: 'reauthentication_required' })(config)
      return { status: 201, statusText: 'Created', data: 'saved', headers: new AxiosHeaders(), config }
    }
    expect((await client.post('/admin/groups/', {})).data).toBe('saved')
    expect(handler).toHaveBeenCalledTimes(1)
    expect(calls).toBe(2)
  })

  it('reads the step-up code from download error blobs and stops when cancelled', async () => {
    const { default: client, setStepUpHandler } = await import('../index')
    const handler = vi.fn().mockResolvedValue(false)
    setStepUpHandler(handler)
    const body = new Blob([JSON.stringify({ code: 'reauthentication_required' })], { type: 'application/json' })
    client.defaults.adapter = failing(403, body as unknown as Record<string, unknown>)
    await expect(client.get('/members/export-excel/', { responseType: 'blob' })).rejects.toBeInstanceOf(AxiosError)
    expect(handler).toHaveBeenCalledTimes(1)
  })
})
