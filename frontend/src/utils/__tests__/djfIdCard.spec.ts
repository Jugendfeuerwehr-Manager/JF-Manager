import { describe, expect, it } from 'vitest'
import { CARD_FIELDS, CARD_HEIGHT, CARD_WIDTH, buildIdCardPdf, fittingFontSize, type CardValues } from '../djfIdCard'
import { correctChannel, hexToRgb, simulateChannel } from '../idCardPhoto'

const values: CardValues = {
  vorname: 'Mia', name: 'Test', geburtsdatum: '04.05.2014', strasse: 'Musterweg 1', plzWohnort: '12345 Musterstadt',
  gemeindeOrt: '', vonBis: '', stadtOrt: 'Musterstadt', stadtOrtsteil: 'Mitte', seitDem: '03.11.2026', datumUnterschrift: '24.11.2026'
}

describe('DJF membership card', () => {
  it('prints only the values, on the card size of the template', () => {
    const doc = buildIdCardPdf({ values, formerMember: null, offset: { x: 0, y: 0 }, guides: false, title: 'Ausweis', font: 'clear' })
    expect(doc.pageSize).toEqual({ width: CARD_WIDTH, height: CARD_HEIGHT })
    const content = doc.content as { text?: string; canvas?: unknown; absolutePosition: { x: number; y: number } }[]
    expect(content.some((entry) => entry.canvas)).toBe(false)
    const vorname = content.find((entry) => entry.text === 'Mia')!
    // Field "Vorname" of the template: x 34.3, top edge 850.394 − 725.6.
    expect(vorname.absolutePosition.x).toBeCloseTo(CARD_FIELDS.vorname.x + 2)
    expect(vorname.absolutePosition.y).toBeGreaterThan(124.79)
    expect(content.find((entry) => entry.text === '')).toBeUndefined()
  })

  it('moves everything by the printer offset and draws guides for a test print', () => {
    const plain = buildIdCardPdf({ values, formerMember: true, offset: { x: 0, y: 0 }, guides: false, title: 'A', font: 'clear' })
    const moved = buildIdCardPdf({ values, formerMember: true, offset: { x: 10, y: -5 }, guides: true, title: 'A', font: 'clear' })
    const first = (doc: typeof plain) => (doc.content as { text?: string; absolutePosition: { x: number; y: number } }[]).find((entry) => entry.text === 'Mia')!
    expect(first(moved).absolutePosition.x - first(plain).absolutePosition.x).toBeCloseTo(28.35, 1)
    expect(first(moved).absolutePosition.y - first(plain).absolutePosition.y).toBeCloseTo(-14.17, 1)
    expect(JSON.stringify(moved.content)).toContain('"dash"')
  })

  it('prints bold, in the typewriter font when chosen', () => {
    const doc = buildIdCardPdf({ values, formerMember: null, offset: { x: 0, y: 0 }, guides: false, title: 'A', font: 'typewriter' })
    const vorname = (doc.content as { text?: string; font?: string; bold?: boolean }[]).find((entry) => entry.text === 'Mia')!
    expect(vorname).toMatchObject({ font: 'CourierPrime', bold: true })
  })

  it('shrinks values that would run past their line', () => {
    expect(fittingFontSize('Mia', 180)).toBe(10)
    expect(fittingFontSize('Maximiliane-Charlotte Sophie', 80)).toBeLessThan(10)
  })
})

describe('photo colour correction for the yellow card', () => {
  const yellow = hexToRgb('#ffe680')

  it('leaves channels the paper reflects fully', () => {
    expect(correctChannel(120, yellow.r, 1)).toBe(120)
  })

  it('lifts the blue channel so less yellow ink lands on yellow paper', () => {
    const corrected = correctChannel(100, yellow.b, 1)
    expect(corrected).toBeGreaterThan(100)
    expect(simulateChannel(corrected, yellow.b)).toBeGreaterThan(simulateChannel(100, yellow.b))
    expect(correctChannel(100, yellow.b, 0)).toBe(100)
  })
})
