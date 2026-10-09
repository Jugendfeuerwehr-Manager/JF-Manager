import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SegmentedControl from '../SegmentedControl.vue'

describe('SegmentedControl', () => {
  it('shows a bare count when no spoken label is given', () => {
    const w = mount(SegmentedControl, { props: { modelValue: 'a', label: 'Ansicht', options: [{ value: 'a', label: 'Alle', count: 3 }] } })
    expect(w.get('.segmented__count').text()).toBe('3')
    expect(w.get('.segmented__count').attributes('aria-hidden')).toBeUndefined()
    expect(w.find('.sr-only').exists()).toBe(false)
  })

  it('announces the count with context instead of the bare number', () => {
    const w = mount(SegmentedControl, {
      props: { modelValue: 'a', label: 'Bereich', options: [{ value: 'a', label: 'Anträge', count: 2, countLabel: '2 offene Anträge' }] },
    })
    expect(w.get('.segmented__count').attributes('aria-hidden')).toBe('true')
    expect(w.get('button .sr-only').text()).toBe(', 2 offene Anträge')
  })
})
