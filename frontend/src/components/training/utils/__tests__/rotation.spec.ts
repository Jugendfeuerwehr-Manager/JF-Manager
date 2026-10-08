import { describe, expect, it } from 'vitest'
import { buildRotation, type RotationInput, type RotationStation } from '../rotation'

const station = (title: string): RotationStation => ({ key: title, title, location: `${title}-Ort`, instructors: [], libraryBlock: null })
const groups = (n: number) => Array.from({ length: n }, (_, i) => ({ id: i + 1, name: `G${i + 1}` }))

function input(overrides: Partial<RotationInput> = {}): RotationInput {
  return {
    groups: groups(3), stations: ['A', 'B', 'C'].map(station), startOffset: 10, stationDuration: 20, transition: 5,
    breakAfterRound: null, breakDuration: 0, sessionDuration: 120, allGroups: true, ...overrides,
  }
}

describe('buildRotation', () => {
  it('lets every group visit every station once without double use', () => {
    const plan = buildRotation(input(), 1)
    expect(plan.rounds.map((r) => r.cells.map((c) => c.station!.title).join(''))).toEqual(['ABC', 'BCA', 'CAB'])
    for (const g of [0, 1, 2]) {
      expect(new Set(plan.rounds.map((r) => r.cells[g]!.station!.title))).toEqual(new Set(['A', 'B', 'C']))
    }
    expect(plan.rounds.map((r) => [r.start, r.end])).toEqual([[10, 30], [35, 55], [60, 80]])
    expect(plan.end).toBe(80)
    const transitions = plan.blocks.filter((b) => b.kind === 'transition')
    expect(transitions.map((b) => [b.start_offset_minutes, b.duration_minutes, b.group_ids])).toEqual([[30, 5, []], [55, 5, []]])
    expect(plan.blocks.filter((b) => b.kind === 'station')).toHaveLength(9)
  })

  it('marks free rounds when there are more groups than stations', () => {
    const plan = buildRotation(input({ groups: groups(3), stations: [station('A'), station('B')] }), 1)
    expect(plan.rounds).toHaveLength(3)
    const free = plan.blocks.filter((b) => b.kind === 'free')
    expect(free).toHaveLength(3)
    expect(free.every((b) => b.title === 'Freie Runde')).toBe(true)
    // Each group has exactly one free round and visits both stations.
    for (const g of [1, 2, 3]) expect(free.filter((b) => b.group_ids![0] === g)).toHaveLength(1)
  })

  it('reports idle stations when there are more stations than groups', () => {
    const plan = buildRotation(input({ groups: groups(2), stations: ['A', 'B', 'C'].map(station), allGroups: false }), 1)
    expect(plan.rounds).toHaveLength(3)
    expect(plan.rounds.map((r) => r.idleStations.map((s) => s.title))).toEqual([['C'], ['A'], ['B']])
    expect(plan.blocks.filter((b) => b.kind === 'free')).toHaveLength(0)
    expect(plan.blocks.find((b) => b.kind === 'transition')!.group_ids).toEqual([1, 2])
  })

  it('replaces one change-over by a pause and enforces the time frame', () => {
    const plan = buildRotation(input({ breakAfterRound: 2, breakDuration: 15 }), 1)
    expect(plan.blocks.filter((b) => b.kind !== 'station').map((b) => [b.kind, b.start_offset_minutes, b.duration_minutes]))
      .toEqual([['transition', 30, 5], ['break', 55, 15]])
    expect(plan.end).toBe(90)
    expect(() => buildRotation(input({ sessionDuration: 79 }), 1)).toThrow('endet nach 80 Minuten')
    expect(() => buildRotation(input({ breakAfterRound: 3, breakDuration: 10 }), 1)).toThrow('zwischen zwei Runden')
    expect(() => buildRotation(input({ stations: [] }), 1)).toThrow('Station')
    expect(() => buildRotation(input({ stations: [station(' ')] }), 1)).toThrow('Titel')
  })
})
