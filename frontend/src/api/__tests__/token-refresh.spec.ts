import { beforeEach, describe, expect, it, vi } from 'vitest'
import axios, { AxiosError, AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'

function expired(config: InternalAxiosRequestConfig) {
  return new AxiosError('Expired', 'ERR_BAD_REQUEST', config, undefined, {
    status: 401, statusText: 'Unauthorized', data: {}, headers: new AxiosHeaders(), config
  })
}

describe('token refresh', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.restoreAllMocks()
    localStorage.clear()
    localStorage.setItem('accessToken', 'expired')
    localStorage.setItem('refreshToken', 'original-refresh')
  })

  it('shares concurrent refresh and saves the rotated refresh credential', async () => {
    let resolveRefresh!: (value: { data: { access: string; refresh: string } }) => void
    const refresh = vi.spyOn(axios, 'post').mockImplementation(() => new Promise(resolve => { resolveRefresh = resolve }))
    const { default: client } = await import('../index')
    client.defaults.adapter = async (config) => {
      if (config.headers.Authorization === 'Bearer expired') throw expired(config)
      return { status: 200, statusText: 'OK', data: 'done', headers: new AxiosHeaders(), config }
    }
    const first = client.get('/members/')
    const second = client.get('/services/')
    await vi.waitFor(() => expect(refresh).toHaveBeenCalledTimes(1))
    resolveRefresh({ data: { access: 'fresh', refresh: 'rotated-refresh' } })
    expect((await Promise.all([first, second])).map(r => r.data)).toEqual(['done', 'done'])
    expect(localStorage.getItem('refreshToken')).toBe('rotated-refresh')
    expect(localStorage.getItem('accessToken')).toBe('fresh')
  })

  it('does not attempt refresh for an incorrect login', async () => {
    const refresh = vi.spyOn(axios, 'post')
    const { default: client } = await import('../index')
    client.defaults.adapter = async config => { throw expired(config) }
    await expect(client.post('/auth/login/', {})).rejects.toBeInstanceOf(AxiosError)
    expect(refresh).not.toHaveBeenCalled()
  })

  it('does not restore credentials after logout during refresh', async () => {
    let resolveRefresh!: (value: { data: { access: string; refresh: string } }) => void
    const refresh = vi.spyOn(axios, 'post').mockImplementation(() => new Promise(resolve => { resolveRefresh = resolve }))
    const { default: client } = await import('../index')
    client.defaults.adapter = async config => { throw expired(config) }
    const request = client.get('/members/')
    const assertion = expect(request).rejects.toThrow('Anmeldung wurde zwischenzeitlich geändert.')
    await vi.waitFor(() => expect(refresh).toHaveBeenCalledTimes(1))
    localStorage.clear()
    resolveRefresh({ data: { access: 'fresh', refresh: 'rotated-refresh' } })
    await assertion
    expect(localStorage.getItem('accessToken')).toBeNull()
    expect(localStorage.getItem('refreshToken')).toBeNull()
  })
})
