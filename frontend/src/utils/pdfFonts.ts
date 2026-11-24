/**
 * Extra fonts for pdfmake beyond its bundled Roboto. The files ship with the app (assets) and
 * are fetched only when a document needs them.
 */
import courierPrimeBold from '@/assets/fonts/courier-prime/CourierPrime-Bold.ttf?url'

export interface PdfFontContainer {
  vfs: Record<string, string>
  fonts: Record<string, { normal: string; bold: string; italics: string; bolditalics: string }>
}

async function base64Of(url: string) {
  const bytes = new Uint8Array(await (await fetch(url)).arrayBuffer())
  let binary = ''
  for (let index = 0; index < bytes.length; index += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000))
  }
  return btoa(binary)
}

let typewriter: Promise<PdfFontContainer> | null = null

/** Courier Prime Bold (SIL OFL) under the family name ``CourierPrime``. */
export function typewriterFont(): Promise<PdfFontContainer> {
  typewriter ??= base64Of(courierPrimeBold).then((data) => ({
    vfs: { 'CourierPrime-Bold.ttf': data },
    fonts: {
      CourierPrime: {
        normal: 'CourierPrime-Bold.ttf',
        bold: 'CourierPrime-Bold.ttf',
        italics: 'CourierPrime-Bold.ttf',
        bolditalics: 'CourierPrime-Bold.ttf'
      }
    }
  }))
  return typewriter
}
