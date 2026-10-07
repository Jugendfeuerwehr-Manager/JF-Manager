import { describe, expect, it } from 'vitest'
import type { TrainingBlock } from '@/types/training'
import { materialSummary, stationCards } from '../handoutSummary'

let id = 1
const block = (title: string, start: number, extra: Partial<TrainingBlock> = {}): TrainingBlock => ({
  id: id++, title, content: '<p>Ablauf</p>', session: 1, groups: [], library_block: null, library_block_title: null,
  duration_minutes: 25, start_offset_minutes: start, position_order: 0, color: '', nextcloud_folder_url: '',
  created_at: '', updated_at: '', media: [], attachments: [], kind: 'station', ...extra,
})
const bambini = { id: 1, name: 'Bambini' }
const jugend = { id: 2, name: 'Jugend' }
const leinen = { item: null, variant: null, quantity: 6, label: 'Übungsleinen' }
const toni = { id: 7, name: 'Toni Trainer' }

describe('handoutSummary', () => {
  const blocks = [
    block('Knoten', 0, { station_key: 'k', groups: [bambini], location: 'Halle', instructors: [toni], materials: [leinen], safety_notes: 'Handschuhe' }),
    block('Schlauch', 0, { station_key: 's', groups: [jugend], materials: [{ item: 5, variant: null, quantity: 2, label: 'C-Schlauch' }] }),
    block('Knoten', 30, { station_key: 'k', groups: [jugend], location: 'Halle', instructors: [toni], materials: [leinen] }),
    block('Schlauch', 30, { station_key: 's', groups: [bambini], materials: [{ item: 5, variant: null, quantity: 2, label: 'C-Schlauch' }] }),
    block('Begrüßung', 60, { kind: 'block', materials: [{ item: 5, variant: null, quantity: 1, label: 'C-Schlauch' }] }),
  ]

  it('prints one card per rotation station with every slot', () => {
    const cards = stationCards(blocks)
    expect(cards.map((c) => c.title)).toEqual(['Knoten', 'Schlauch'])
    expect(cards[0]).toMatchObject({ location: 'Halle', safetyNotes: 'Handschuhe', instructors: [toni] })
    expect(cards[0]!.slots).toEqual([{ start: 0, end: 25, groups: 'Bambini' }, { start: 30, end: 55, groups: 'Jugend' }])
  })

  it('merges unlinked stations only when they are identical', () => {
    const older = [block('Erste Hilfe', 0, { groups: [bambini] }), block('Erste Hilfe', 30, { groups: [jugend] })]
    expect(stationCards(older)).toHaveLength(1)
    const adapted = [...older, block('Erste Hilfe', 60, { groups: [jugend], content: '<p>Für Ältere</p>' })]
    expect(stationCards(adapted)).toHaveLength(2)
  })

  it('counts station material once and other blocks each time', () => {
    expect(materialSummary(blocks)).toEqual([
      { label: 'C-Schlauch', quantity: 3, usedAt: ['Schlauch', 'Begrüßung'] },
      { label: 'Übungsleinen', quantity: 6, usedAt: ['Knoten'] },
    ])
  })
})
