import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ConsentPanel from '../organisms/ConsentPanel.vue'
import { privacyApi } from '@/api/privacy'
import type { ConsentRecord } from '@/types/privacy'

vi.mock('@/api/privacy', () => ({ privacyApi: { consents: vi.fn(), recordConsent: vi.fn(), subjectAccess: vi.fn() } }))

const record = (id: number, kind: string, status: 'granted' | 'withdrawn', label: string): ConsentRecord => ({
  id, kind, kind_label: label, status, status_label: status === 'granted' ? 'Erteilt' : 'Widerrufen',
  source: 'staff', source_label: 'Von der Leitung erfasst', text_version: '', recorded_at: '2026-10-01T10:00:00Z',
  recorded_by_name: 'Leitung', note: '',
})

const render = (canEdit = true, canExport = false) => mount(ConsentPanel, {
  props: { subject: { field: 'member', id: 7 }, canEdit, canExport },
  global: { plugins: [PrimeVue], directives: { tooltip: {} } },
})

describe('ConsentPanel', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })

  it('shows the newest state per kind and keeps the history', async () => {
    vi.mocked(privacyApi.consents).mockResolvedValue({ data: [
      record(2, 'photo_public', 'withdrawn', 'Fotos öffentlich'),
      record(1, 'photo_public', 'granted', 'Fotos öffentlich'),
    ] } as never)
    const wrapper = render(); await flushPromises()
    expect(privacyApi.consents).toHaveBeenCalledWith({ field: 'member', id: 7 })
    const items = wrapper.findAll('.consent-panel__list li')
    expect(items).toHaveLength(1)
    expect(items[0]!.text()).toContain('Widerrufen')
    expect(wrapper.text()).toContain('Verlauf (2 Einträge)')
  })

  it('offers no recording without the change right', async () => {
    vi.mocked(privacyApi.consents).mockResolvedValue({ data: [] } as never)
    const wrapper = render(false); await flushPromises()
    expect(wrapper.text()).toContain('Keine Einwilligungen erfasst.')
    expect(wrapper.text()).not.toContain('Erfassen')
  })

  it('offers the data copy only with the export right', async () => {
    vi.mocked(privacyApi.consents).mockResolvedValue({ data: [] } as never)
    expect(render(false, false).text()).not.toContain('Datenauskunft')
    vi.mocked(privacyApi.subjectAccess).mockResolvedValue({ data: new Blob(['zip']) } as never)
    URL.createObjectURL = vi.fn(() => 'blob:x')
    const wrapper = render(false, true); await flushPromises()
    const button = wrapper.findAll('button').find(b => b.text().includes('Datenauskunft'))!
    await button.trigger('click'); await flushPromises()
    expect(privacyApi.subjectAccess).toHaveBeenCalledWith({ field: 'member', id: 7 })
  })
})
