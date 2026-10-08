import { afterEach, describe, expect, it, vi } from 'vitest'
import pdfMake from 'pdfmake/build/pdfmake'
import type { MemberListDetail } from '@/types/lists'
import { useListPdf } from '../useListPdf'

const list = {
  name: 'Ausflug Äöü', description: '', color: '#0e7490',
  entries: [{ checked: true, notes: 'Fiktive Notiz', member: { full_name: 'Test Person' } }],
} as unknown as MemberListDetail

afterEach(() => vi.restoreAllMocks())

describe('list PDF export', () => {
  it('generates a real PDF with bundled fonts and awaits the download', async () => {
    const createPdf = pdfMake.createPdf.bind(pdfMake)
    let bytes: Uint8Array | undefined
    const download = vi.fn()
    vi.spyOn(pdfMake, 'createPdf').mockImplementation(definition => {
      const document = createPdf(definition)
      download.mockImplementation(async () => { bytes = await document.getBuffer() })
      return { download } as unknown as ReturnType<typeof pdfMake.createPdf>
    })
    await useListPdf().generateChecklist(list)
    expect(download).toHaveBeenCalledWith(expect.stringMatching(/^Ausflug Äöü_.*\.pdf$/))
    expect(bytes).toBeDefined()
    expect(new TextDecoder().decode(bytes!.slice(0, 5))).toBe('%PDF-')
  })

  it('propagates asynchronous download errors to the caller', async () => {
    const error = new Error('PDF download failed')
    // A delayed rejection distinguishes awaiting download from fire-and-forget.
    const download = vi.fn(() => new Promise<void>((_, reject) => setTimeout(() => reject(error), 0)))
    vi.spyOn(pdfMake, 'createPdf').mockReturnValue({ download } as unknown as ReturnType<typeof pdfMake.createPdf>)
    await expect(useListPdf().generateChecklist(list)).rejects.toBe(error)
  })
})
