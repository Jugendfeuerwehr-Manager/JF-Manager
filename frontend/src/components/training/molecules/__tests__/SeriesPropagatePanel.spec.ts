import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SeriesPropagatePanel from '../SeriesPropagatePanel.vue'
import type { PropagationPreview, PropagationRow } from '@/types/training'

const api = vi.hoisted(() => ({ propagationPreview: vi.fn(), propagateSeries: vi.fn() }))
vi.mock('@/api/training', () => ({ trainingSessionsApi: api }))

function row(overrides: Partial<PropagationRow>): PropagationRow {
  return {
    session_id: 2, date: '2099-01-12', original_date: '2099-01-12', title: 'Dienstabend', status: 'draft',
    action: 'update', reason: 'Wird angepasst.', changes: ['Zeit: 18:00–20:00 → 18:30–20:30'], overridable: false,
    ...overrides,
  }
}

function preview(rows: PropagationRow[], token = 'a'.repeat(64)): PropagationPreview {
  const counts = { update: 0, unchanged: 0, deviating: 0, history: 0, conflict: 0 }
  rows.forEach((r) => { counts[r.action] += 1 })
  return { source_id: 1, source_revision: 4, preview_token: token, occurrences: rows, counts }
}

function mountPanel() {
  return mount(SeriesPropagatePanel, {
    props: { sessionId: 1 },
    global: {
      stubs: {
        Button: { props: ['label', 'disabled'], emits: ['click'], template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}</button>' },
        Checkbox: { props: ['modelValue', 'inputId'], emits: ['update:modelValue'], template: '<input type="checkbox" :id="inputId" :checked="modelValue" @change="$emit(\'update:modelValue\', $event.target.checked)" />' },
        RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
      },
    },
  })
}

describe('SeriesPropagatePanel', () => {
  beforeEach(() => {
    api.propagationPreview.mockReset()
    api.propagateSeries.mockReset()
  })

  it('keeps deviating and historical dates by default and lists concrete changes', async () => {
    api.propagationPreview.mockResolvedValue({ data: preview([
      row({}),
      row({ session_id: 3, date: '2099-01-20', original_date: '2099-01-19', action: 'deviating', overridable: true, reason: 'Abweichender Einzeltermin bleibt standardmäßig erhalten.' }),
      row({ session_id: 4, action: 'history', changes: [], reason: 'Abgeschlossen oder abgesagt; bleibt unverändert.' }),
    ]) })
    const wrapper = mountPanel()
    await flushPromises()
    expect(wrapper.text()).toContain('1 werden geändert · 1 abweichend erhalten · 1 historisch')
    expect(wrapper.text()).toContain('Zeit: 18:00–20:00 → 18:30–20:30')
    expect(wrapper.text()).toContain('(Serie: 19.01.2099)')
    expect(wrapper.findAll('input[type="checkbox"]')).toHaveLength(1)
    expect(api.propagationPreview).toHaveBeenCalledWith(1, { include_deviating: [] })
  })

  it('reloads the preview with an explicit override and applies exactly that preview', async () => {
    api.propagationPreview
      .mockResolvedValueOnce({ data: preview([row({ session_id: 3, action: 'deviating', overridable: true })]) })
      .mockResolvedValueOnce({ data: preview([row({ session_id: 3, action: 'update', overridable: true })], 'b'.repeat(64)) })
      .mockResolvedValue({ data: preview([row({ session_id: 3, action: 'unchanged', overridable: false, changes: [] })], 'c'.repeat(64)) })
    api.propagateSeries.mockResolvedValue({ data: { updated: 1, session_ids: [3] } })
    const wrapper = mountPanel()
    await flushPromises()
    await wrapper.find('input[type="checkbox"]').setValue(true)
    await flushPromises()
    expect(api.propagationPreview).toHaveBeenLastCalledWith(1, { include_deviating: [3] })
    await wrapper.findAll('button').find((b) => b.text() === '1 Folgetermine ändern')!.trigger('click')
    await flushPromises()
    expect(api.propagateSeries).toHaveBeenCalledWith(1, { include_deviating: [3], preview_token: 'b'.repeat(64) })
    expect(wrapper.emitted('propagated')).toEqual([[1]])
    expect(wrapper.text()).toContain('1 Folgetermine geändert.')
  })

  it('shows the server preview on conflict and changes nothing locally', async () => {
    api.propagationPreview.mockResolvedValue({ data: preview([row({})]) })
    api.propagateSeries.mockRejectedValue({ response: { status: 409, data: { preview: preview([row({ action: 'deviating', overridable: true })], 'd'.repeat(64)) } } })
    const wrapper = mountPanel()
    await flushPromises()
    await wrapper.findAll('button').find((b) => b.text() === '1 Folgetermine ändern')!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Nichts wurde übertragen')
    expect(wrapper.text()).toContain('0 werden geändert · 1 abweichend erhalten')
    expect(wrapper.emitted('propagated')).toBeUndefined()
  })
})
