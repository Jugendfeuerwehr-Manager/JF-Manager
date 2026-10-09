import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePortalStore } from '../portal'
import { portalApi } from '@/api/portal'

vi.mock('@/api/portal', () => ({ portalApi: { me: vi.fn() } }))
vi.mock('@/router', () => ({ default: { push: vi.fn(), currentRoute: { value: { path: '/' } } } }))

describe('portal store', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('loads the portal overview', async () => {
    const data = { account: { first_name: 'A', last_name: 'B', email: 'a@b.de' }, people: [] }
    vi.mocked(portalApi.me).mockResolvedValue({ data } as never)
    const store = usePortalStore()
    await store.fetchMe()
    expect(store.me).toEqual(data)
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('records an error when loading fails', async () => {
    vi.mocked(portalApi.me).mockRejectedValue(new Error('boom'))
    const store = usePortalStore()
    await store.fetchMe()
    expect(store.error).toBeTruthy()
  })
})
