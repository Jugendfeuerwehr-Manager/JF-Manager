import { describe, expect, it } from 'vitest'
import { telHref } from '../contactHref'

describe('telHref', () => {
  it('keeps digits and a leading plus only', () => {
    expect(telHref('+49 151 / 234-56')).toBe('tel:+4915123456')
    expect(telHref('0170 555 0123')).toBe('tel:01705550123')
    expect(telHref('  ')).toBe('')
    expect(telHref(null)).toBe('')
  })
})
