import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import PortalConsentsView from '../PortalConsentsView.vue'
import { portalApi } from '@/api/portal'

vi.mock('@/api/portal', () => ({ portalApi: { consents: vi.fn(), changeConsent: vi.fn() } }))

const overview = (status: 'granted' | 'withdrawn' | null) => ({
  data: {
    kinds: [{ slug: 'photo_public', label: 'Fotos öffentlich', description: 'Website und Presse', version: 1 }],
    people: [{
      member_id: 7,
      name: 'Tim Muster',
      consents: { photo_public: status ? { status, recorded_at: '2026-11-02T10:00:00Z', recorded_by_name: 'Anna Muster', source: 'self', text_version: 'photo_public:v1' } : null },
    }],
  },
})

const button = (wrapper: ReturnType<typeof mount>, label: string) => wrapper.findAll('button').find(b => b.text().includes(label))

describe('PortalConsentsView', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('grants a consent for a child', async () => {
    vi.mocked(portalApi.consents).mockResolvedValue(overview(null) as never)
    vi.mocked(portalApi.changeConsent).mockResolvedValue(overview('granted') as never)
    const wrapper = mount(PortalConsentsView, { global: { plugins: [PrimeVue] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Noch nicht erteilt')
    await button(wrapper, 'Einwilligen')!.trigger('click')
    await flushPromises()
    expect(portalApi.changeConsent).toHaveBeenCalledWith({ member: 7, kind: 'photo_public', status: 'granted' })
    expect(wrapper.text()).toContain('Erteilt am 02.11.2026 von Anna Muster')
  })

  it('withdraws from the granted consent after a confirmation', async () => {
    vi.mocked(portalApi.consents).mockResolvedValue(overview('granted') as never)
    vi.mocked(portalApi.changeConsent).mockResolvedValue(overview('withdrawn') as never)
    const wrapper = mount(PortalConsentsView, { global: { plugins: [PrimeVue] } })
    await flushPromises()
    await button(wrapper, 'Widerrufen')!.trigger('click')
    expect(portalApi.changeConsent).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Wirklich widerrufen?')
    await wrapper.findAll('button').filter(b => b.text().includes('Widerrufen'))[0]!.trigger('click')
    await flushPromises()
    expect(portalApi.changeConsent).toHaveBeenCalledWith({ member: 7, kind: 'photo_public', status: 'withdrawn' })
    expect(wrapper.text()).toContain('Widerrufen am 02.11.2026')
  })
})
