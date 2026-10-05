import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PrivateMedia from '../PrivateMedia.vue'
import { privateMediaPath } from '@/utils/privateMedia'
import api from '@/api'

vi.mock('@/api', () => ({ default: { defaults: { baseURL: '/api/v1' }, get: vi.fn() } }))

afterEach(() => { vi.restoreAllMocks() })

describe('private media clients', () => {
  it('never treats a foreign lookalike endpoint as the authenticated API', () => {
    expect(privateMediaPath('https://foreign.example/api/v1/private-media/training/1/')).toBeNull()
    expect(privateMediaPath('/api/v1/private-media/training/1/')).toBe('/private-media/training/1/')
  })

  it('fetches an authorized image and revokes its local URL on unmount', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: new Blob(['image'], { type: 'image/png' }) })
    URL.createObjectURL = vi.fn(() => 'blob:private-test')
    URL.revokeObjectURL = vi.fn()
    const wrapper = mount(PrivateMedia, { props: { src: '/api/v1/private-media/training/1/' } })
    await flushPromises()
    expect(api.get).toHaveBeenCalledWith('/private-media/training/1/', expect.objectContaining({ responseType: 'blob' }))
    expect(wrapper.find('img').attributes('src')).toBe('blob:private-test')
    wrapper.unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:private-test')
  })

  it('does not display active content even when a legacy filename claims to be an image', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: new Blob(['<script>bad()</script>'], { type: 'text/html' }) })
    const wrapper = mount(PrivateMedia, { props: { src: '/api/v1/private-media/training/1/' } })
    await flushPromises()
    expect(wrapper.find('img').attributes('src')).toBeUndefined()
    wrapper.unmount()
  })
})
