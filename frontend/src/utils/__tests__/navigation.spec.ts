import { afterEach, describe, expect, it, vi } from 'vitest'
import { hardNavigate, safeReturnPath } from '../navigation'

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

describe('hardNavigate', () => {
  const assign = vi.fn()
  afterEach(() => { assign.mockReset(); vi.unstubAllGlobals() })

  it.each([
    ['/login?next=%2Fa', '/login?next=%2Fa'],
    ['/admin/', '/admin/'],
    ['//evil.example', '/'],
    ['https://evil.example', '/'],
    ['/\\evil.example', '/'],
  ])('navigates %j to %j', (path, expected) => {
    vi.stubGlobal('location', { assign })
    hardNavigate(path)
    expect(assign).toHaveBeenCalledWith(expected)
  })
})
