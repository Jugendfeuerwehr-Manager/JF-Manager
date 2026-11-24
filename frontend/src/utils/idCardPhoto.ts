/**
 * Passport photo for the yellow DJF card: crop to 35:45 and compensate the paper tone.
 *
 * Printing is subtractive, so the card shows roughly ink × paper per channel. A yellow card
 * reflects little blue, which makes faces look sallow or greenish. The correction divides by the
 * paper tone (less yellow ink where the paper already is yellow), blended by ``strength``.
 * Channels the paper hardly reflects cannot be restored; ``MIN_PAPER`` keeps the division sane.
 */

export interface Rgb {
  r: number
  g: number
  b: number
}

/** Default tone of the pre-printed DJF card; calibrate against a test print. */
export const DEFAULT_PAPER = '#ffe680'
const MIN_PAPER = 0.35
/** 45 mm at 300 dpi */
const OUTPUT_HEIGHT = 531

export function hexToRgb(hex: string): Rgb {
  const value = /^#?([0-9a-f]{6})$/i.exec(hex.trim())?.[1] ?? 'ffffff'
  return {
    r: Number.parseInt(value.slice(0, 2), 16),
    g: Number.parseInt(value.slice(2, 4), 16),
    b: Number.parseInt(value.slice(4, 6), 16)
  }
}

/** One channel (0–255) corrected for a paper channel (0–255). */
export function correctChannel(value: number, paper: number, strength: number) {
  const reflectance = Math.max(paper / 255, MIN_PAPER)
  const ideal = Math.min(255, value / reflectance)
  return Math.round(value + (ideal - value) * Math.min(Math.max(strength, 0), 1))
}

/** How a channel roughly looks once printed on the paper. */
export function simulateChannel(value: number, paper: number) {
  return Math.round((value * paper) / 255)
}

function mapPixels(source: ImageData, paper: Rgb, map: (value: number, paper: number) => number) {
  const out = new ImageData(source.width, source.height)
  for (let index = 0; index < source.data.length; index += 4) {
    out.data[index] = map(source.data[index]!, paper.r)
    out.data[index + 1] = map(source.data[index + 1]!, paper.g)
    out.data[index + 2] = map(source.data[index + 2]!, paper.b)
    out.data[index + 3] = 255
  }
  return out
}

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Bild konnte nicht gelesen werden'))
    image.src = src
  })
}

function toDataUrl(data: ImageData) {
  const canvas = document.createElement('canvas')
  canvas.width = data.width
  canvas.height = data.height
  canvas.getContext('2d')!.putImageData(data, 0, 0)
  return canvas.toDataURL('image/jpeg', 0.92)
}

/** Centre crop to the passport aspect ratio, as pixels on a white ground. */
export async function cropPassport(src: string, aspect: number): Promise<ImageData> {
  const image = await loadImage(src)
  let width = image.naturalWidth
  let height = Math.round(width / aspect)
  if (height > image.naturalHeight) {
    height = image.naturalHeight
    width = Math.round(height * aspect)
  }
  const canvas = document.createElement('canvas')
  canvas.height = Math.min(OUTPUT_HEIGHT, height)
  canvas.width = Math.round(canvas.height * aspect)
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = 'white'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(
    image,
    (image.naturalWidth - width) / 2,
    (image.naturalHeight - height) / 2,
    width,
    height,
    0,
    0,
    canvas.width,
    canvas.height
  )
  return ctx.getImageData(0, 0, canvas.width, canvas.height)
}

export interface PreparedPhoto {
  /** what goes into the PDF */
  print: string
  /** previews: as printed on the card without and with correction */
  onCardPlain: string
  onCardCorrected: string
}

export function preparePhoto(cropped: ImageData, paperHex: string, strength: number): PreparedPhoto {
  const paper = hexToRgb(paperHex)
  const corrected = mapPixels(cropped, paper, (value, tone) => correctChannel(value, tone, strength))
  return {
    print: toDataUrl(corrected),
    onCardPlain: toDataUrl(mapPixels(cropped, paper, simulateChannel)),
    onCardCorrected: toDataUrl(mapPixels(corrected, paper, simulateChannel))
  }
}
