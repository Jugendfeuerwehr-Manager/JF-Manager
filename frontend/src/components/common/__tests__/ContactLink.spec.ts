import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ContactLink from '../ContactLink.vue'

describe('ContactLink', () => {
  it('normalises phone numbers for tel: links but shows the original text', () => {
    const w = mount(ContactLink, { props: { kind: 'phone', value: '+49 (0)170 / 123-456' } })
    expect(w.get('a').attributes('href')).toBe('tel:+490170123456')
    expect(w.text()).toBe('+49 (0)170 / 123-456')
  })

  it('handles numbers without a plus', () => {
    const w = mount(ContactLink, { props: { kind: 'phone', value: '0170 123 456' } })
    expect(w.get('a').attributes('href')).toBe('tel:0170123456')
  })

  it('renders mailto links and supports a custom label', () => {
    const w = mount(ContactLink, { props: { kind: 'email', value: ' a@example.org ', label: 'Mail' } })
    expect(w.get('a').attributes('href')).toBe('mailto:a@example.org')
    expect(w.text()).toBe('Mail')
  })

  it('renders a dash instead of a link for empty values', () => {
    for (const value of ['', null, undefined, '   ']) {
      const w = mount(ContactLink, { props: { kind: 'email', value } })
      expect(w.find('a').exists()).toBe(false)
      expect(w.text()).toBe('–')
    }
  })
})
