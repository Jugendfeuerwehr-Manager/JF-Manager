import { describe, expect, it } from 'vitest'
import { describeUserAgent } from '../userAgent'

describe('describeUserAgent', () => {
  it('names browser and system', () => {
    expect(describeUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0')).toBe('Firefox unter Windows')
    expect(describeUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1')).toBe('Safari unter iOS')
    expect(describeUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/129.0 Safari/537.36 Edg/129.0')).toBe('Edge unter Linux')
  })

  it('falls back for unknown agents', () => {
    expect(describeUserAgent('')).toBe('Unbekanntes Gerät')
  })
})
