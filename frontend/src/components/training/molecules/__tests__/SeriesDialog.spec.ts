import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SeriesDialog from '../SeriesDialog.vue'
import type { SeriesPreview } from '@/types/training'

const api = vi.hoisted(() => ({ seriesPreview: vi.fn(), generateSeries: vi.fn() }))
vi.mock('@/api/training', () => ({ trainingSessionsApi: api }))

function preview(overrides: Partial<SeriesPreview> = {}): SeriesPreview {
  return {
    series_id: null, root_id: 1, root_revision: 3, frequency: 'MONTHLY', anchor_date: '2099-01-31',
    window_start: '2099-01-31', window_end: '2099-04-30', preview_token: 'a'.repeat(64),
    occurrences: [
      { date: '2099-02-28', action: 'new', session_id: null, actual_date: null, reason: 'Eigenständiger Entwurf', warnings: ['Überschneidung mit „Erste Hilfe“'] },
      { date: '2099-03-31', action: 'preserved', session_id: 7, actual_date: '2099-04-01', reason: 'Verschobener Einzeltermin bleibt erhalten.', warnings: [] },
    ],
    counts: { new: 1, preserved: 1, skipped: 0, conflict: 0 },
    ...overrides,
  }
}

function mountDialog() {
  return mount(SeriesDialog, {
    props: { visible: true, sessionId: 1 },
    global: {
      stubs: {
        Dialog: { template: '<div><slot /><slot name="footer" /></div>' },
        Button: { props: ['label', 'disabled', 'type'], emits: ['click'], template: '<button :type="type || \'button\'" :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>' },
        InputText: { props: ['modelValue'], template: '<input :value="modelValue" />' },
        RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
      },
    },
  })
}

describe('SeriesDialog', () => {
  beforeEach(() => {
    api.seriesPreview.mockReset()
    api.generateSeries.mockReset()
  })

  it('shows the complete preview with preserved real occurrences and warnings', async () => {
    api.seriesPreview.mockResolvedValue({ data: preview() })
    const wrapper = mountDialog()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('1 neu · 1 vorhanden · 0 ausgelassen · 0 Konflikte')
    expect(text).toContain('28.02.2099')
    expect(text).toContain('Überschneidung mit „Erste Hilfe“')
    expect(wrapper.find('a[href="/training/sessions/7/plan"]').text()).toContain('01.04.2099')
    expect(api.generateSeries).not.toHaveBeenCalled()
  })

  it('sends the preview token and shows a refreshed preview on conflict without creating', async () => {
    api.seriesPreview.mockResolvedValue({ data: preview() })
    const changed = preview({ preview_token: 'b'.repeat(64), counts: { new: 0, preserved: 2, skipped: 0, conflict: 0 } })
    api.generateSeries.mockRejectedValue({ response: { status: 409, data: { code: 'series_preview_changed', preview: changed } } })
    const wrapper = mountDialog()
    await flushPromises()
    await wrapper.findAll('button').find((b) => b.text() === '1 Termine anlegen')!.trigger('click')
    await flushPromises()
    expect(api.generateSeries).toHaveBeenCalledWith(1, expect.objectContaining({ preview_token: 'a'.repeat(64) }))
    expect(wrapper.text()).toContain('Nichts wurde angelegt')
    expect(wrapper.text()).toContain('0 neu · 2 vorhanden')
    expect(wrapper.emitted('generated')).toBeUndefined()
  })

  it('reports created dates and reloads the preview', async () => {
    api.seriesPreview.mockResolvedValue({ data: preview() })
    api.generateSeries.mockResolvedValue({ data: { created: 1, session_ids: [9] } })
    const wrapper = mountDialog()
    await flushPromises()
    await wrapper.findAll('button').find((b) => b.text() === '1 Termine anlegen')!.trigger('click')
    await flushPromises()
    expect(wrapper.emitted('generated')).toEqual([[1]])
    expect(wrapper.text()).toContain('1 Termine angelegt.')
    expect(api.seriesPreview).toHaveBeenCalledTimes(2)
  })
})
