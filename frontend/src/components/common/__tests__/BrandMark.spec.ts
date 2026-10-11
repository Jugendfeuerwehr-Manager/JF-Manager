import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import BrandMark from '../BrandMark.vue'

describe('BrandMark', () => {
  it('renders a decorative logo at the default size', () => {
    const svg = mount(BrandMark).get('svg')
    expect(svg.attributes('aria-hidden')).toBe('true')
    expect(svg.attributes('width')).toBe('36')
    expect(svg.attributes('height')).toBe('36')
  })

  it('accepts a custom size', () => {
    const svg = mount(BrandMark, { props: { size: 44 } }).get('svg')
    expect(svg.attributes('width')).toBe('44')
    expect(svg.attributes('height')).toBe('44')
  })
})
