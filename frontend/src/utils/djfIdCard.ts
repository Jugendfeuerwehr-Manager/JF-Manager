/**
 * DJF membership card ("Mitgliedsausweis der Deutschen Jugendfeuerwehr"): only the values are
 * printed onto the pre-printed card, never its frame.
 *
 * Positions come from the official print template (Druckvorlage_DJF_Mitgliedsausweis.pdf,
 * 106 × 300 mm): its form fields give the value boxes, the photo frame was measured from the
 * non-printing artwork layer. PDF points, origin top left.
 */
import type { Content, TDocumentDefinitions } from 'pdfmake/interfaces'

export const CARD_WIDTH = 300.472
export const CARD_HEIGHT = 850.394
const MM = 72 / 25.4
const FONT_SIZE = 10

interface Box {
  x: number
  y: number
  w: number
  h: number
}

/** Form field rectangle of the template, converted from PDF (bottom left) to top left. */
function fromPdf(x1: number, y1: number, x2: number, y2: number): Box {
  return { x: x1, y: CARD_HEIGHT - y2, w: x2 - x1, h: y2 - y1 }
}

export const CARD_FIELDS = {
  vorname: fromPdf(34.3, 708.9, 218.8, 725.6),
  name: fromPdf(34.3, 675.0, 218.8, 691.6),
  geburtsdatum: fromPdf(23.6, 597.2, 277.0, 613.3),
  strasse: fromPdf(23.6, 563.2, 277.0, 578.3),
  plzWohnort: fromPdf(23.6, 530.3, 277.0, 545.9),
  // "war Mitglied der Jugendfeuerwehr" (earlier membership elsewhere)
  gemeindeOrt: fromPdf(23.6, 472.6, 277.0, 487.3),
  vonBis: fromPdf(23.1, 437.7, 105.4, 454.3),
  ja: fromPdf(120.8, 438.7, 131.6, 450.0),
  nein: fromPdf(150.8, 438.7, 161.6, 450.0),
  // "ist Mitglied der Jugendfeuerwehr der Freiwilligen Feuerwehr"
  stadtOrt: fromPdf(23.6, 354.7, 277.0, 370.3),
  stadtOrtsteil: fromPdf(23.6, 318.7, 277.0, 335.6),
  seitDem: fromPdf(23.6, 282.7, 277.0, 300.2),
  datumUnterschrift: fromPdf(100.2, 224.4, 181.3, 241.0)
} as const

/** Inner photo frame (38 × 55 mm); the photo sits at the top, the seal overlaps its lower edge. */
export const PHOTO_FRAME: Box = { x: 23.6, y: 665.6, w: 106.8, h: 156.4 }
/** Passport photo 35 × 45 mm, centred in the frame. */
export const PHOTO: Box = {
  x: PHOTO_FRAME.x + (PHOTO_FRAME.w - 35 * MM) / 2,
  y: PHOTO_FRAME.y + 4,
  w: 35 * MM,
  h: 45 * MM
}
export const PHOTO_ASPECT = 35 / 45

/** Typewriter (Courier Prime Bold, bundled) or a clear sans (Roboto Medium); both print bold. */
export type CardFont = 'typewriter' | 'clear'
export const CARD_FONTS: Record<CardFont, { label: string; pdf: string; glyph: number }> = {
  typewriter: { label: 'Schreibmaschine', pdf: 'CourierPrime', glyph: 0.6 },
  clear: { label: 'Klar', pdf: 'Roboto', glyph: 0.55 }
}

export type CardTextField = Exclude<keyof typeof CARD_FIELDS, 'ja' | 'nein'>
export type CardValues = Record<CardTextField, string>

export interface IdCardInput {
  values: CardValues
  /** earlier membership: ticks "Ja" or "Nein"; null ticks nothing */
  formerMember: boolean | null
  /** data URL, already cropped to 35:45 and colour-corrected */
  photo?: string
  /** printer calibration in millimetres; positive moves right and down */
  offset: { x: number; y: number }
  /** draw the field boxes and photo frame for a test print on plain paper */
  guides: boolean
  title: string
  font: CardFont
}

/** Shrinks long values so they stay on the one line the card has; ``glyph`` is the average
 * glyph width relative to the font size (monospace 0.6). */
export function fittingFontSize(text: string, width: number, glyph = CARD_FONTS.clear.glyph) {
  if (!text) return FONT_SIZE
  return Math.max(6, Math.min(FONT_SIZE, (width - 4) / (text.length * glyph)))
}

/** Where a value sits: shared by the PDF and the on-screen preview. */
export function valuePlacement(box: Box, value: string, font: CardFont) {
  const fontSize = fittingFontSize(value, box.w, CARD_FONTS[font].glyph)
  return { x: box.x + 2, y: box.y + (box.h - fontSize * 1.15) / 2, fontSize }
}

function text(box: Box, value: string, font: CardFont, dx: number, dy: number): Content | null {
  const clean = value.trim()
  if (!clean) return null
  const place = valuePlacement(box, clean, font)
  return {
    text: clean,
    font: CARD_FONTS[font].pdf,
    bold: true,
    fontSize: place.fontSize,
    absolutePosition: { x: place.x + dx, y: place.y + dy }
  }
}

function cross(box: Box, dx: number, dy: number): Content {
  return {
    canvas: [
      { type: 'line', x1: 1.5, y1: 1.5, x2: box.w - 1.5, y2: box.h - 1.5, lineWidth: 1.2 },
      { type: 'line', x1: box.w - 1.5, y1: 1.5, x2: 1.5, y2: box.h - 1.5, lineWidth: 1.2 }
    ],
    absolutePosition: { x: box.x + dx, y: box.y + dy }
  }
}

function guides(dx: number, dy: number): Content {
  const outline = (box: Box) => ({
    type: 'rect' as const,
    x: box.x + dx,
    y: box.y + dy,
    w: box.w,
    h: box.h,
    lineWidth: 0.4,
    lineColor: '#9ca3af',
    dash: { length: 2 }
  })
  return {
    canvas: [
      { type: 'rect', x: 0.5, y: 0.5, w: CARD_WIDTH - 1, h: CARD_HEIGHT - 1, lineWidth: 0.4, lineColor: '#9ca3af' },
      ...Object.values(CARD_FIELDS).map(outline),
      outline(PHOTO_FRAME)
    ],
    absolutePosition: { x: 0, y: 0 }
  }
}

export function buildIdCardPdf(input: IdCardInput): TDocumentDefinitions {
  const dx = input.offset.x * MM
  const dy = input.offset.y * MM
  const content: Content[] = []
  if (input.guides) content.push(guides(dx, dy))
  for (const [key, box] of Object.entries(CARD_FIELDS)) {
    if (key === 'ja' || key === 'nein') continue
    const entry = text(box, input.values[key as CardTextField] ?? '', input.font, dx, dy)
    if (entry) content.push(entry)
  }
  if (input.formerMember !== null) content.push(cross(input.formerMember ? CARD_FIELDS.ja : CARD_FIELDS.nein, dx, dy))
  if (input.photo) {
    content.push({ image: input.photo, width: PHOTO.w, height: PHOTO.h, absolutePosition: { x: PHOTO.x + dx, y: PHOTO.y + dy } })
  }
  return {
    pageSize: { width: CARD_WIDTH, height: CARD_HEIGHT },
    pageMargins: [0, 0, 0, 0],
    info: { title: input.title },
    content,
    defaultStyle: { font: 'Roboto', fontSize: FONT_SIZE, color: '#000000' }
  }
}
