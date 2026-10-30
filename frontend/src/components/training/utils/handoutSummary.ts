import type { BlockMaterial, InstructorMini, TrainingBlock, TrainingSessionHandout } from '@/types/training'

/** One printable card per station; a rotation station appears once with all its slots. */
export interface StationCard {
  key: string
  /** First block of the station; its content and attachments describe the station. */
  blockId: number
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
      key, blockId: block.id, title: block.title, location: block.location ?? '', instructors: [], slots: [],
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

// ── Shared by the handout view and the PDF ──────────────────────────────────

/** Clock time of an offset from the session start; '+25′' without a start time. */
export function clockTime(offset: number, startTime?: string | null): string {
  if (!startTime) return `+${offset}′`
  const [h = 0, m = 0] = startTime.split(':').map(Number)
  const total = h * 60 + m + offset
  return `${String(Math.floor(total / 60) % 24).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

export function timeSpan(start: number, end: number, startTime?: string | null) {
  return `${clockTime(start, startTime)}–${clockTime(end, startTime)}`
}

export const blockEnd = (b: TrainingBlock) => b.start_offset_minutes + b.duration_minutes

export const byStart = (a: TrainingBlock, b: TrainingBlock) =>
  a.start_offset_minutes - b.start_offset_minutes || a.position_order - b.position_order

export interface HandoutLane {
  key: string
  label: string
  groupId: number | null
}

/** One lane per group (session groups first); a single lane when nothing is grouped. */
export function handoutLanes(h: Pick<TrainingSessionHandout, 'groups' | 'blocks'>): HandoutLane[] {
  const lanes = new Map<number, HandoutLane>()
  for (const g of h.groups ?? []) lanes.set(g.id, { key: String(g.id), label: g.name, groupId: g.id })
  for (const block of h.blocks) {
    for (const g of block.groups ?? []) {
      if (!lanes.has(g.id)) lanes.set(g.id, { key: String(g.id), label: g.name, groupId: g.id })
    }
  }
  return lanes.size ? [...lanes.values()] : [{ key: 'all', label: 'Alle Gruppen', groupId: null }]
}

/** The blocks a lane's group takes part in, blocks for all groups included. */
export function laneBlocks(blocks: TrainingBlock[], lane: HandoutLane) {
  return blocks
    .filter((b) => lane.groupId === null || !b.groups?.length || b.groups.some((g) => g.id === lane.groupId))
    .sort(byStart)
}

/** Contiguous lane ranges a block covers; a block for all groups spans every lane. */
export function blockLaneRuns(block: TrainingBlock, lanes: HandoutLane[]): Array<[number, number]> {
  if (!block.groups?.length) return [[0, lanes.length - 1]]
  const ids = new Set(block.groups.map((g) => g.id))
  const runs: Array<[number, number]> = []
  lanes.forEach((lane, i) => {
    if (lane.groupId === null || !ids.has(lane.groupId)) return
    const last = runs[runs.length - 1]
    if (last && last[1] === i - 1) last[1] = i
    else runs.push([i, i])
  })
  return runs
}

export interface InstructorDuty {
  title: string
  location: string
  /** [start, end] offsets */
  slots: Array<[number, number]>
}

export interface InstructorAssignment {
  /** null: stations nobody has been assigned to yet */
  id: number | null
  name: string
  duties: InstructorDuty[]
}

/** Who is where: every instructor with their stations and blocks, unstaffed stations last. */
export function instructorAssignments(blocks: TrainingBlock[]): InstructorAssignment[] {
  const people = new Map<number, InstructorAssignment>()
  const add = (person: InstructorMini, duty: InstructorDuty) => {
    const entry = people.get(person.id) ?? { id: person.id, name: person.name, duties: [] }
    entry.duties.push(duty)
    people.set(person.id, entry)
  }
  const cards = stationCards(blocks)
  for (const card of cards) {
    const duty = { title: card.title, location: card.location, slots: card.slots.map((s): [number, number] => [s.start, s.end]) }
    for (const person of card.instructors) add(person, duty)
  }
  for (const b of blocks.filter((b) => b.kind !== 'station').sort(byStart)) {
    for (const person of b.instructors ?? []) add(person, { title: b.title, location: b.location ?? '', slots: [[b.start_offset_minutes, blockEnd(b)]] })
  }
  const result = [...people.values()].sort((a, b) => a.name.localeCompare(b.name, 'de'))
  for (const entry of result) entry.duties.sort((a, b) => (a.slots[0]?.[0] ?? 0) - (b.slots[0]?.[0] ?? 0))
  const open = cards.filter((c) => !c.instructors.length)
  if (open.length) {
    result.push({ id: null, name: 'unbesetzt', duties: open.map((c) => ({ title: c.title, location: c.location, slots: c.slots.map((s): [number, number] => [s.start, s.end]) })) })
  }
  return result
}
