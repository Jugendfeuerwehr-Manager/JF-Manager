import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import LegalPageView from '../LegalPageView.vue'
import { privacyApi } from '@/api/privacy'

vi.mock('@/api/privacy', () => ({ privacyApi: { publicPage: vi.fn() } }))
vi.mock('vue-router', () => ({ useRouter: () => ({ back: vi.fn(), push: vi.fn() }) }))

const render = () => mount(LegalPageView, {
  props: { kind: 'privacy' },
  global: { plugins: [PrimeVue], stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } },
})

describe('LegalPageView', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('renders the published text without active markup', async () => {
    vi.mocked(privacyApi.publicPage).mockResolvedValue({ data: {
      kind: 'privacy', version: 3, title: 'Datenschutzerklärung',
      body: '<p>Wir verarbeiten</p><img src="x" onerror="alert(1)">', published_at: '2026-10-01T10:00:00Z',
    } } as never)
    const wrapper = render(); await flushPromises()
    expect(privacyApi.publicPage).toHaveBeenCalledWith('privacy')
    expect(wrapper.find('h1').text()).toBe('Datenschutzerklärung')
    expect(wrapper.html()).not.toContain('onerror')
    expect(wrapper.text()).toContain('Version 3')
  })

  it('explains when nothing is published yet', async () => {
    vi.mocked(privacyApi.publicPage).mockRejectedValue({ response: { status: 404, data: { detail: 'Dieser Rechtstext ist noch nicht veröffentlicht.' } } })
    const wrapper = render(); await flushPromises()
    expect(wrapper.text()).toContain('noch nicht veröffentlicht')
  })
})
