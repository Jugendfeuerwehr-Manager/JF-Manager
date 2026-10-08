import type { PlannerBlock, TrainingBlockMove } from '@/types/training'

export interface PlannedMove {
  id: number
  title: string
  from: number
  to: number
  fromGroups: number[]
  toGroups: number[]
  values: TrainingBlockMove
}

/** Explicit local operations. Merely requesting a preview never mutates blocks. */
export function previewPlanAction(
  blocks: PlannerBlock[], duration: number,
  kind: 'swap' | 'shift_following', sourceId: number | null, targetOrDelta: number | null,
): PlannedMove[] {
  const source = blocks.find((b) => b.id === sourceId)
  if (!source) throw new Error('Wähle den ersten Baustein.')
  const move = (block: PlannerBlock, to: number, groups = block.groupIds): PlannedMove => {
    if (to < 0 || to + block.duration_minutes > duration) {
      throw new Error(`„${block.title}“ würde außerhalb des Terminrahmens liegen.`)
    }
    return {
      id: block.id, title: block.title, from: block.start_offset_minutes, to,
      fromGroups: [...block.groupIds], toGroups: [...groups],
      values: { start_offset_minutes: to, groups: [...groups] },
    }
  }
  if (kind === 'swap') {
    const target = blocks.find((b) => b.id === targetOrDelta)
    if (!target || target.id === source.id) throw new Error('Wähle einen anderen Baustein zum Tauschen.')
    return [move(source, target.start_offset_minutes, target.groupIds),
      move(target, source.start_offset_minutes, source.groupIds)]
  }
  if (!Number.isInteger(targetOrDelta) || !targetOrDelta) throw new Error('Gib eine Verschiebung in ganzen Minuten an.')
  return blocks.filter((b) => b.start_offset_minutes >= source.start_offset_minutes
    && (source.allGroups || b.allGroups || b.groupIds.some((id) => source.groupIds.includes(id))))
    .map((b) => move(b, b.start_offset_minutes + targetOrDelta!))
}
