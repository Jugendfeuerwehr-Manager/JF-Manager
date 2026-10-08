import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import PortalPushCard from '../PortalPushCard.vue'

vi.mock('@/api', () => ({ default: { get: vi.fn().mockResolvedValue({ data: { enabled: true, public_key: 'AAAA' } }), post: vi.fn(), delete: vi.fn() } }))
vi.mock('@/utils/pwa', () => ({ pwaSupported: false, getWorker: vi.fn(), disableDevicePush: vi.fn() }))

describe('PortalPushCard', () => {
  it('is hidden when push is unsupported', async () => {
    const wrapper = mount(PortalPushCard, { global: { plugins: [createPinia(), PrimeVue] } })
    await flushPromises()
    expect(wrapper.find('section').exists()).toBe(false)
  })
})
