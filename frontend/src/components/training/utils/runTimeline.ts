import type { BlockMaterial, InstructorMini, TrainingBlock } from '@/types/training'

/**
 * Field execution (TRAIN-04): the plan is cut into sections at every block
 * start. The device clock picks the current section; nothing is saved.
 */
export interface RunSection {
  index: number
  start: number
  end: number
  blocks: TrainingBlock[]
  /** 1-based rotation round when the section contains stations. */
  round: number | null
  label: string
}

export interface RunCard {
  key: string
  title: string
  kind: TrainingBlock['kind']
  location: string
  instructors: InstructorMini[]
  groupsNow: string
  groupsNext: string
  blocks: TrainingBlock[]
}

export type RunPhase = 'before' | 'running' | 'after'

export interface RunPosition {
  phase: RunPhase
  /** Minutes since the planned start (fractional, may be negative). */
  minute: number
  /** Current section while running, otherwise the first (before) or last (after). */
  index: number
  /** Calendar days from today to the exercise (0 = today). */
  daysAway: number
}

const end = (b: TrainingBlock) => b.start_offset_minutes + b.duration_minutes

export function buildSections(blocks: TrainingBlock[]): RunSection[] {
  const starts = [...new Set(blocks.map((b) => b.start_offset_minutes))].sort((a, b) => a - b)
  const last = Math.max(0, ...blocks.map(end))
  const sections: RunSection[] = []
  starts.forEach((start, index) => {
    const next = starts[index + 1] ?? last
    const active = blocks
      .filter((b) => b.start_offset_minutes <= start && start < end(b))
      .sort((a, b) => a.start_offset_minutes - b.start_offset_minutes || a.position_order - b.position_order || a.id - b.id)
    // A section lasts until its blocks end; a gap before the next start is its own section.
    const stop = Math.min(next, Math.max(...active.map(end)))
    sections.push({ index, start, end: stop, blocks: active, round: null, label: '' })
    if (stop < next) sections.push({ index, start: stop, end: next, blocks: [], round: null, label: '' })
  })
  const rounds = sections.filter((s) => s.blocks.some((b) => b.kind === 'station'))
  sections.forEach((section, index) => {
    section.index = index
    const round = rounds.indexOf(section)
    section.round = round >= 0 ? round + 1 : null
    section.label = round >= 0
      ? `Runde ${round + 1} von ${rounds.length}`
      : [...new Set(section.blocks.map((b) => b.title))].join(' · ') || 'Übergang'
  })
  return sections
}

/** ``date`` YYYY-MM-DD and ``startTime`` HH:MM[:SS] in the device's local time. */
export function runPosition(sections: RunSection[], date: string, startTime: string, now: Date): RunPosition {
  const [y, m, d] = date.split('-').map(Number)
  const [h, min] = startTime.split(':').map(Number)
  const start = new Date(y!, m! - 1, d!, h ?? 0, min ?? 0)
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const daysAway = Math.round((new Date(y!, m! - 1, d!).getTime() - today.getTime()) / 86_400_000)
  const minute = (now.getTime() - start.getTime()) / 60_000
  const finish = sections.length ? sections[sections.length - 1]!.end : 0
  if (!sections.length || minute < sections[0]!.start) return { phase: 'before', minute, index: 0, daysAway }
  if (minute >= finish) return { phase: 'after', minute, index: sections.length - 1, daysAway }
  let index = 0
  sections.forEach((s, i) => { if (s.start <= minute) index = i })
  return { phase: 'running', minute, index, daysAway }
}

function groupNames(blocks: TrainingBlock[]) {
  if (blocks.some((b) => !b.groups.length)) return 'Alle Gruppen'
  return [...new Set(blocks.flatMap((b) => b.groups.map((g) => g.name)))].join(', ')
}

function cardKey(b: TrainingBlock) {
  return b.kind === 'station' ? b.station_key || `${b.title}|${b.location ?? ''}` : `block-${b.id}`
}

/** Stations of a section with the group now and the group that comes next. */
export function sectionCards(sections: RunSection[], index: number): RunCard[] {
  const section = sections[index]
  if (!section) return []
  const nextRound = sections.slice(index + 1).find((s) => s.round !== null)
  const cards = new Map<string, RunCard>()
  for (const block of section.blocks) {
    const key = cardKey(block)
    const card = cards.get(key) ?? {
      key, title: block.title, kind: block.kind ?? 'block', location: block.location ?? '',
      instructors: [], groupsNow: '', groupsNext: '', blocks: [],
    }
    card.blocks.push(block)
    for (const person of block.instructors ?? []) {
      if (!card.instructors.some((i) => i.id === person.id)) card.instructors.push(person)
    }
    cards.set(key, card)
  }
  for (const card of cards.values()) {
    card.groupsNow = groupNames(card.blocks)
    if (card.kind === 'station' && nextRound) {
      const next = nextRound.blocks.filter((b) => cardKey(b) === card.key)
      card.groupsNext = next.length ? groupNames(next) : 'frei'
    }
  }
  return [...cards.values()]
}

/** First section from ``index`` on in which the person instructs, with its cards. */
export function myNextCards(sections: RunSection[], index: number, userId: number | null) {
  if (userId === null) return null
  for (let i = Math.max(0, index); i < sections.length; i++) {
    const cards = sectionCards(sections, i).filter((c) => c.instructors.some((p) => p.id === userId))
    if (cards.length) return { index: i, cards }
  }
  return null
}

export function materialLines(card: RunCard): BlockMaterial[] {
  // Linked blocks share their materials; otherwise list each block's needs once.
  const seen = new Set<string>()
  const lines: BlockMaterial[] = []
  for (const block of card.blocks) {
    for (const m of block.materials ?? []) {
      const id = `${m.item ?? ''}|${m.variant ?? ''}|${m.label}|${m.quantity}`
      if (!seen.has(id)) {
        seen.add(id)
        lines.push(m)
      }
    }
  }
  return lines
}
