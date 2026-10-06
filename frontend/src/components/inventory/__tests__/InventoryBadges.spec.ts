import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import StockBadge from '../atoms/StockBadge.vue'
import ScopeBadge from '../atoms/ScopeBadge.vue'

describe('StockBadge', () => {
  it('highlights only empty and low stock and says so in text', () => {
    const ok = mount(StockBadge, { props: { quantity: 12 } })
    const low = mount(StockBadge, { props: { quantity: 2 } })
    const empty = mount(StockBadge, { props: { quantity: 0 } })
    expect(ok.classes()).toContain('stock-badge--ok')
    expect(ok.text()).toBe('12 – ausreichend')
    expect(low.classes()).toContain('stock-badge--low')
    expect(low.text()).toContain('niedriger Bestand')
    expect(empty.classes()).toContain('stock-badge--empty')
    expect(empty.text()).toContain('nicht vorrätig')
  })
})

describe('ScopeBadge', () => {
  it('names organisation-wide stock instead of a bare letter', () => {
    const wrapper = mount(ScopeBadge)
    expect(wrapper.text()).toContain('Zentral')
    expect(wrapper.text()).toContain('gehört der Organisation')
  })
})
