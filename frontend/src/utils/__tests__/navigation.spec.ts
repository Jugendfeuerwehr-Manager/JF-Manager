import { describe, expect, it } from 'vitest'
import { safeReturnPath } from '../navigation'

describe('safeReturnPath', () => {
  it('keeps relative paths with one leading slash, also quick-action links', () => {
    expect(safeReturnPath('/a/abc:def_ghi')).toBe('/a/abc:def_ghi')
    expect(safeReturnPath('/portal/termine/3?x=1')).toBe('/portal/termine/3?x=1')
  })

  it.each([
    '//evil.example', '///evil.example', 'https://evil.example', 'http://evil.example/a', 'javascript:alert(1)',
    '/\\evil.example', '\\\\evil.example', 'evil.example', '', '/login', '/a/x\n//evil', undefined, null, 5,
  ])('rejects %j', (value) => {
    expect(safeReturnPath(value)).toBe('/')
  })
})
