import type { GroupMini, InstructorMini, TrainingBlockCreate } from '@/types/training'

export interface RotationStation {
  title: string
  location: string
  instructors: InstructorMini[]
  libraryBlock: number | null
}

export interface RotationInput {
  groups: GroupMini[]
  stations: RotationStation[]
  startOffset: number
  stationDuration: number
  transition: number
  /** Pause after this round (1-based) instead of the change-over; null = none. */
  breakAfterRound: number | null
  breakDuration: number
  sessionDuration: number
  /** All exercise groups take part: shared blocks then apply to all groups. */
  allGroups: boolean
}

export interface RotationCell {
  group: GroupMini
  station: RotationStation | null // null = explicitly marked free round
}

export interface RotationRound {
  number: number
  start: number
  end: number
  cells: RotationCell[]
  idleStations: RotationStation[]
}

export interface RotationPlan {
  rounds: RotationRound[]
  end: number
  blocks: Array<TrainingBlockCreate & { instructors: InstructorMini[] }>
}

export const MAX_ROTATION_ITEMS = 20

/**
 * Every group visits every station once in the given order, one group per
 * station and round. Unequal numbers create explicitly marked free rounds
 * instead of double use. Throws a readable error for invalid input.
 */
export function buildRotation(input: RotationInput, sessionId: number): RotationPlan {
  const { groups, stations, stationDuration, transition, breakAfterRound, breakDuration } = input
  if (!groups.length) throw new Error('Mindestens eine Gruppe auswählen.')
  if (!stations.length) throw new Error('Mindestens eine Station anlegen.')
  if (groups.length > MAX_ROTATION_ITEMS || stations.length > MAX_ROTATION_ITEMS) {
    throw new Error(`Höchstens ${MAX_ROTATION_ITEMS} Gruppen und Stationen.`)
  }
  if (stations.some((s) => !s.title.trim())) throw new Error('Jede Station braucht einen Titel.')
  if (!(stationDuration >= 1)) throw new Error('Die Stationsdauer muss mindestens eine Minute betragen.')
  if (!(transition >= 0) || !(input.startOffset >= 0)) throw new Error('Beginn und Wechselzeit dürfen nicht negativ sein.')
  const rounds = Math.max(groups.length, stations.length)
  if (breakAfterRound !== null && (breakAfterRound < 1 || breakAfterRound >= rounds || !(breakDuration >= 1))) {
    throw new Error(`Die Pause muss zwischen zwei Runden liegen (nach Runde 1 bis ${rounds - 1}) und mindestens eine Minute dauern.`)
  }
  const shared = input.allGroups ? [] : groups.map((g) => g.id)
  const plan: RotationPlan = { rounds: [], end: input.startOffset, blocks: [] }
  let time = input.startOffset
  for (let r = 0; r < rounds; r++) {
    const round: RotationRound = { number: r + 1, start: time, end: time + stationDuration, cells: [], idleStations: [] }
    const used = new Set<number>()
    groups.forEach((group, g) => {
      const slot = (g + r) % rounds
      const station = slot < stations.length ? stations[slot]! : null
      if (station) used.add(slot)
      round.cells.push({ group, station })
      plan.blocks.push(station
        ? {
            session: sessionId, title: station.title, kind: 'station', location: station.location,
            group_ids: [group.id], start_offset_minutes: time, duration_minutes: stationDuration,
            library_block: station.libraryBlock, instructors: station.instructors,
          }
        : {
            session: sessionId, title: 'Freie Runde', kind: 'free', group_ids: [group.id],
            start_offset_minutes: time, duration_minutes: stationDuration, instructors: [],
          })
    })
    round.idleStations = stations.filter((_, index) => !used.has(index))
    plan.rounds.push(round)
    time = round.end
    if (r < rounds - 1) {
      const isBreak = breakAfterRound === r + 1
      const length = isBreak ? breakDuration : transition
      if (length > 0) {
        plan.blocks.push({
          session: sessionId, title: isBreak ? 'Pause' : 'Wechsel', kind: isBreak ? 'break' : 'transition',
          group_ids: shared, start_offset_minutes: time, duration_minutes: length, instructors: [],
        })
        time += length
      }
    }
  }
  plan.end = time
  if (plan.end > input.sessionDuration) {
    throw new Error(`Der Ablauf endet nach ${plan.end} Minuten, die Übung dauert ${input.sessionDuration} Minuten. Dauer, Wechselzeit oder Beginn anpassen.`)
  }
  return plan
}
