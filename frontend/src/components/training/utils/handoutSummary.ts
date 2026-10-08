import type { BlockMaterial, InstructorMini, TrainingBlock } from '@/types/training'

/** One printable card per station; a rotation station appears once with all its slots. */
export interface StationCard {
  key: string
  title: string
  location: string
  instructors: InstructorMini[]
  slots: Array<{ start: number; end: number; groups: string }>
  learningObjective: string
  safetyNotes: string
  materials: BlockMaterial[]
}

export interface MaterialLine {
  label: string
  quantity: number
  usedAt: string[]
}

// Linked stations share station_key; older or unlinked rotations are merged only
// when they are identical, so a station adapted for one age group keeps its own card.
function stationKey(b: TrainingBlock) {
  return b.station_key || JSON.stringify([b.title, b.location ?? '', b.content, b.learning_objective ?? '', b.safety_notes ?? ''])
}

export function stationCards(blocks: TrainingBlock[]): StationCard[] {
  const cards = new Map<string, StationCard>()
  const ordered = [...blocks].sort((a, b) => a.start_offset_minutes - b.start_offset_minutes || a.position_order - b.position_order)
  for (const block of ordered) {
    if (block.kind !== 'station') continue
    const key = stationKey(block)
    const card = cards.get(key) ?? {
      key, title: block.title, location: block.location ?? '', instructors: [], slots: [],
      learningObjective: block.learning_objective ?? '', safetyNotes: block.safety_notes ?? '',
      materials: (block.materials ?? []).map((m) => ({ ...m })),
    }
    for (const person of block.instructors ?? []) {
      if (!card.instructors.some((i) => i.id === person.id)) card.instructors.push(person)
    }
    card.slots.push({
      start: block.start_offset_minutes,
      end: block.start_offset_minutes + block.duration_minutes,
      groups: block.groups.length ? block.groups.map((g) => g.name).join(', ') : 'Alle Gruppen',
    })
    cards.set(key, card)
  }
  return [...cards.values()]
}

/**
 * Material to prepare: a station's material is used by every group in turn and
 * counts once; other blocks count each. Planning figures only, no stock booking.
 */
export function materialSummary(blocks: TrainingBlock[]): MaterialLine[] {
  const sources: Array<{ title: string; materials: BlockMaterial[] }> = [
    ...stationCards(blocks).map((c) => ({ title: c.title, materials: c.materials })),
    ...blocks.filter((b) => b.kind !== 'station').map((b) => ({ title: b.title, materials: b.materials ?? [] })),
  ]
  const lines = new Map<string, MaterialLine>()
  for (const source of sources) {
    for (const m of source.materials) {
      const key = m.item ? `${m.item}|${m.variant ?? ''}` : `text|${m.label.trim().toLocaleLowerCase('de')}`
      const line = lines.get(key) ?? { label: m.label, quantity: 0, usedAt: [] }
      line.quantity += m.quantity
      if (!line.usedAt.includes(source.title)) line.usedAt.push(source.title)
      lines.set(key, line)
    }
  }
  return [...lines.values()].sort((a, b) => a.label.localeCompare(b.label, 'de'))
}
