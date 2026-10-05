import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SafeEmailPreview from '../SafeEmailPreview.vue'
import PhoneMockup from '@/components/settings/atoms/PhoneMockup.vue'

describe('isolated email previews', () => {
  it.each([SafeEmailPreview, PhoneMockup])('removes script permissions and sanitizes HTML', (component) => {
    const unsafe = '<script>parent.alert(1)</script><p onclick="alert(1)">Hello</p>'
    const wrapper = mount(component, { props: { html: unsafe, htmlContent: unsafe } })
    const frame = wrapper.find('iframe')
    expect(frame.attributes('sandbox')).toBe('')
    expect(frame.attributes('referrerpolicy')).toBe('no-referrer')
    const source = frame.attributes('srcdoc') ?? ''
    expect(source).toContain("default-src 'none'")
    expect(source).toContain('<p>Hello</p>')
    expect(source).not.toContain('<script>')
    expect(source).not.toContain('onclick')
  })
})
