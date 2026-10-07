import { describe, expect, it } from 'vitest'
import type { TrainingBlock } from '@/types/training'
import { buildSections, materialLines, myNextCards, runPosition, sectionCards } from '../runTimeline'

const red = { id: 1, name: 'Bambini' }
const blue = { id: 2, name: 'Jugend' }
let nextId = 1
function block(title: string, start: number, duration: number, extra: Partial<TrainingBlock> = {}): TrainingBlock {
  return {
    id: nextId++, title, content: '', session: 1, groups: [], library_block: null, library_block_title: null,
    duration_minutes: duration, start_offset_minutes: start, position_order: 0, color: '', nextcloud_folder_url: '',
    created_at: '', updated_at: '', media: [], attachments: [], kind: 'block', ...extra,
  }
}
const toni = { id: 7, name: 'Toni Trainer' }
const plan = [
  block('Begrüßung', 0, 15),
  block('Knoten', 15, 25, { kind: 'station', station_key: 'k', groups: [red], instructors: [toni], location: 'Halle', materials: [{ item: null, variant: null, quantity: 4, label: 'Leinen' }] }),
  block('Schlauch', 15, 25, { kind: 'station', station_key: 's', groups: [blue] }),
  block('Wechsel', 40, 5, { kind: 'transition' }),
  block('Knoten', 45, 25, { kind: 'station', station_key: 'k', groups: [blue], instructors: [toni], location: 'Halle', materials: [{ item: null, variant: null, quantity: 4, label: 'Leinen' }] }),
  block('Schlauch', 45, 25, { kind: 'station', station_key: 's', groups: [red] }),
]

describe('runTimeline', () => {
  const sections = buildSections(plan)

  it('cuts the plan into sections and numbers rotation rounds', () => {
    expect(sections.map((s) => [s.start, s.end, s.label])).toEqual([
      [0, 15, 'Begrüßung'], [15, 40, 'Runde 1 von 2'], [40, 45, 'Wechsel'], [45, 70, 'Runde 2 von 2'],
    ])
  })

  it('turns a gap between blocks into its own transition section', () => {
    const gap = buildSections([block('A', 0, 25, { kind: 'station' }), block('B', 30, 20, { kind: 'station' })])
    expect(gap.map((s) => [s.start, s.end, s.label])).toEqual([[0, 25, 'Runde 1 von 2'], [25, 30, 'Übergang'], [30, 50, 'Runde 2 von 2']])
  })

  it('follows the device clock before, during and after the exercise', () => {
    const at = (h: number, m: number, day = 11) => runPosition(sections, '2026-10-11', '18:00:00', new Date(2026, 9, day, h, m))
    expect(at(17, 35)).toMatchObject({ phase: 'before', index: 0, daysAway: 0 })
    expect(at(17, 35, 9)).toMatchObject({ phase: 'before', daysAway: 2 })
    expect(at(18, 20)).toMatchObject({ phase: 'running', index: 1 })
    expect(at(18, 20).minute).toBe(20)
    expect(at(18, 42)).toMatchObject({ phase: 'running', index: 2 })
    expect(at(19, 10)).toMatchObject({ phase: 'after', index: 3 })
  })

  it('shows each station with the group now and next', () => {
    const cards = sectionCards(sections, 1)
    expect(cards.map((c) => [c.title, c.groupsNow, c.groupsNext, c.location])).toEqual([
      ['Knoten', 'Bambini', 'Jugend', 'Halle'], ['Schlauch', 'Jugend', 'Bambini', ''],
    ])
    expect(sectionCards(sections, 0)[0]).toMatchObject({ title: 'Begrüßung', groupsNow: 'Alle Gruppen', groupsNext: '' })
    // Last round: nothing follows.
    expect(sectionCards(sections, 3)[0]!.groupsNext).toBe('')
  })

  it('finds the own station from now on and lists its material once', () => {
    expect(myNextCards(sections, 0, 7)).toMatchObject({ index: 1 })
    expect(myNextCards(sections, 2, 7)!.cards[0]!.groupsNow).toBe('Jugend')
    expect(myNextCards(sections, 0, 99)).toBeNull()
    expect(materialLines(myNextCards(sections, 1, 7)!.cards[0]!)).toEqual([{ item: null, variant: null, quantity: 4, label: 'Leinen' }])
  })
})
