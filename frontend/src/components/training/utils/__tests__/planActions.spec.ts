import { describe, expect, it } from 'vitest'
import { previewPlanAction } from '../planActions'
import type { PlannerBlock } from '@/types/training'

const block = (id: number, offset: number, groups: number[], duration = 15): PlannerBlock => ({
  id, title: `Block ${id}`, start_offset_minutes: offset, duration_minutes: duration,
  groupIds: groups, allGroups: !groups.length,
}) as PlannerBlock

describe('explicit plan action previews', () => {
  it('shows swapped times and groups without changing originals', () => {
    const blocks = [block(1, 0, [1]), block(2, 30, [2])]
    const moves = previewPlanAction(blocks, 60, 'swap', 1, 2)
    expect(moves.map((m) => m.values)).toEqual([
      { start_offset_minutes: 30, groups: [2] }, { start_offset_minutes: 0, groups: [1] },
    ])
    expect(blocks[0]!.start_offset_minutes).toBe(0)
    expect(blocks[0]!.groupIds).toEqual([1])
  })

  it('shifts only relevant later groups including shared blocks', () => {
    const blocks = [block(1, 0, [1]), block(2, 20, [1]), block(3, 20, [2]), block(4, 40, [])]
    const moves = previewPlanAction(blocks, 90, 'shift_following', 1, 5)
    expect(moves.map((m) => [m.id, m.to])).toEqual([[1, 5], [2, 25], [4, 45]])
    expect(blocks.map((b) => b.start_offset_minutes)).toEqual([0, 20, 20, 40])
  })

  it('shifts every later group when starting at a shared block', () => {
    const blocks = [block(1, 0, [1]), block(2, 20, []), block(3, 40, [2])]
    expect(previewPlanAction(blocks, 90, 'shift_following', 2, 5).map((m) => m.id)).toEqual([2, 3])
  })

  it('rejects previews outside the frame or with incomplete parameters', () => {
    const blocks = [block(1, 0, [1], 30), block(2, 50, [2])]
    expect(() => previewPlanAction(blocks, 60, 'swap', 1, 2)).toThrow('Terminrahmen')
    expect(() => previewPlanAction(blocks, 60, 'shift_following', 1, -5)).toThrow('Terminrahmen')
    expect(() => previewPlanAction(blocks, 60, 'swap', 1, 1)).toThrow('anderen')
    expect(() => previewPlanAction(blocks, 60, 'shift_following', 1, 1.5)).toThrow('ganzen Minuten')
  })
})
