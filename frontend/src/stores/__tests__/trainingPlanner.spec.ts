import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useTrainingPlannerStore } from '../trainingPlanner'
import type { TrainingSessionDetail, TrainingBlock } from '@/types/training'

const api = vi.hoisted(() => ({ plan: vi.fn(), savePlan: vi.fn(), getLibrary: vi.fn() }))
vi.mock('@/api/training', () => ({
  trainingSessionsApi: { plan: api.plan, savePlan: api.savePlan },
  libraryApi: { get: api.getLibrary },
}))

function block(id: number): TrainingBlock {
  return {
    id, title: `Block ${id}`, content: '', session: 1, groups: [], library_block: null,
    library_block_title: null, duration_minutes: 15, start_offset_minutes: 0, position_order: 0,
    color: '', nextcloud_folder_url: '', created_at: '', updated_at: '', media: [], attachments: [],
  }
}
function plan(): TrainingSessionDetail {
  return {
    status: 'draft', requires_service_confirmation: false, can_manage_plan: true,
    id: 1, revision: 1, title: 'Plan', description: '', date: '2030-01-01',
    start_time: '18:00:00', end_time: '20:00:00', location: '', notes: '', groups: [],
    blocks: [block(1), block(2)], department: 1, linked_service_id: null,
    linked_service_start: null, series_parent: null, series_uuid: null, original_date: null, recurrence_rule: null,
    created_by: null, created_by_name: null, created_at: '', updated_at: '',
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.resetAllMocks()
  api.plan.mockResolvedValue({ data: plan() })
})

describe('complete local training drafts', () => {
  it('keeps a released read-only plan free of local mutations', async () => {
    api.plan.mockResolvedValue({ data: { ...plan(), status: 'published', can_manage_plan: false } })
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    store.stageMove(1, { start_offset_minutes: 40 })
    expect(store.isDirty).toBe(false)
    expect(() => store.stageSession({ status: 'cancelled' })).toThrow('Leseberechtigung')
    await expect(store.removeBlock(1)).rejects.toThrow('Leseberechtigung')
    expect(store.blocks).toHaveLength(2)
  })

  it('stages publication with content and never retains service confirmation for a later save', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    store.stageSession({ status: 'published' })
    await store.updateBlockContent(1, { title: 'Veröffentlichter Inhalt' })
    api.savePlan.mockResolvedValue({ data: { ...plan(), status: 'published', revision: 2, linked_service_id: 4 } })
    await store.savePendingMoves(true)
    expect(api.savePlan.mock.calls[0]![1].session).toMatchObject({ status: 'published', confirm_service_change: true })
    expect(store.isDirty).toBe(false)
    expect(store.session!.linked_service_id).toBe(4)
    store.stageSession({ status: 'completed' })
    await store.savePendingMoves()
    expect(api.savePlan.mock.calls[1]![1].session).not.toHaveProperty('confirm_service_change')
  })

  it('stages creation, content, deletion, metadata and movement for one request', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    expect(store.isDirty).toBe(false)
    store.stageMove(1, { start_offset_minutes: 30, groups: [5] })
    await store.updateBlockContent(1, { title: 'Changed', content: '<p>Text</p>' })
    await store.removeBlock(2)
    const added = await store.addBlock({ session: 1, title: 'New' })
    store.stageSession({ title: 'Changed plan', date: '2030-01-01', start_time: '18:00:00', end_time: '20:00:00' })
    expect(added!.id).toBeLessThan(0)
    expect(api.savePlan).not.toHaveBeenCalled()
    expect(store.isDirty).toBe(true)
    api.savePlan.mockResolvedValue({ data: { ...plan(), revision: 2 } })
    await store.savePendingMoves()
    expect(api.savePlan).toHaveBeenCalledTimes(1)
    expect(api.savePlan.mock.calls[0]![1]).toMatchObject({
      expected_revision: 1, session: { title: 'Changed plan' },
      blocks: [{ id: 1, title: 'Changed', content: '<p>Text</p>', start_offset_minutes: 30, group_ids: [5] },
        { title: 'New' }],
    })
    expect(api.savePlan.mock.calls[0]![1].blocks[1]).not.toHaveProperty('id')
    expect(store.isDirty).toBe(false)
    expect(store.session!.revision).toBe(2)
  })

  it('retains the whole draft and expected version after errors for retry', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    store.stageMove(1, { start_offset_minutes: 40 })
    await store.removeBlock(2)
    api.savePlan.mockRejectedValue(new Error('offline'))
    await expect(store.savePendingMoves()).rejects.toThrow('offline')
    expect(store.blocks).toHaveLength(1)
    expect(store.blocks[0]!.start_offset_minutes).toBe(40)
    expect(store.isDirty).toBe(true)
    expect(store.session!.revision).toBe(1)
    api.savePlan.mockResolvedValue({ data: { ...plan(), revision: 2 } })
    await store.savePendingMoves()
    expect(api.savePlan.mock.calls[1]![1]).toEqual(api.savePlan.mock.calls[0]![1])
  })

  it('keeps local edits and exposes the current server snapshot on conflict', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    await store.updateBlockContent(1, { title: 'Local' })
    const current = { ...plan(), title: 'Remote', revision: 2 }
    api.savePlan.mockRejectedValue({ response: { status: 409, data: { current } } })
    await expect(store.savePendingMoves()).rejects.toBeDefined()
    expect(store.blocks[0]!.title).toBe('Local')
    expect(store.conflict!.title).toBe('Remote')
    expect(store.session!.revision).toBe(1)
    expect(store.isDirty).toBe(true)
    store.discardForServerVersion()
    expect(store.session!.revision).toBe(2)
    expect(store.isDirty).toBe(false)
  })

  it('keeps dirty status while saving and prevents concurrent changes/double saves', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    store.stageMove(1, { start_offset_minutes: 20 })
    let resolve!: (value: { data: TrainingSessionDetail }) => void
    api.savePlan.mockReturnValue(new Promise((r) => { resolve = r }))
    const pending = store.savePendingMoves()
    expect(store.isDirty).toBe(true)
    store.stageMove(1, { start_offset_minutes: 50 })
    await expect(store.removeBlock(1)).rejects.toThrow()
    await store.savePendingMoves()
    expect(api.savePlan).toHaveBeenCalledTimes(1)
    expect(store.blocks[0]!.start_offset_minutes).toBe(20)
    resolve({ data: { ...plan(), revision: 2 } })
    await pending
    expect(store.isDirty).toBe(false)
  })

  it('copies library contents before staging an independent new block', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    api.getLibrary.mockResolvedValue({ data: { content: '<p>Snapshot</p>', color: '#123456' } })
    await store.addBlock({ session: 1, title: 'Template', library_block: 7 })
    expect(store.blocks[2]!.content).toBe('<p>Snapshot</p>')
    expect(api.savePlan).not.toHaveBeenCalled()
  })

  it('does not restore an old plan after resetting during a pending save', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    store.stageMove(1, { start_offset_minutes: 20 })
    let resolve!: (value: { data: TrainingSessionDetail }) => void
    api.savePlan.mockReturnValue(new Promise((r) => { resolve = r }))
    const pending = store.savePendingMoves()
    store.reset()
    resolve({ data: { ...plan(), revision: 2 } })
    await pending
    expect(store.session).toBeNull()
    expect(store.blocks).toHaveLength(0)
  })
})

describe('unsaved draft history', () => {
  it('undoes and redoes an entire drag as one action', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    store.beginGesture()
    store.stageMove(1, { start_offset_minutes: 5 })
    store.stageMove(1, { start_offset_minutes: 10 })
    store.stageMove(1, { start_offset_minutes: 15, groups: [5] })
    store.endGesture()
    store.undo()
    expect(store.blocks[0]!.start_offset_minutes).toBe(0)
    expect(store.blocks[0]!.groupIds).toEqual([])
    expect(store.isDirty).toBe(false)
    expect(store.canUndo).toBe(false)
    store.redo()
    expect(store.blocks[0]!.start_offset_minutes).toBe(15)
    expect(store.blocks[0]!.groupIds).toEqual([5])
    expect(store.isDirty).toBe(true)
  })

  it('restores creation/deletion/content and clears redo after a new edit', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    const added = await store.addBlock({ session: 1, title: 'Local' })
    await store.updateBlockContent(added!.id, { title: 'Edited local' })
    await store.removeBlock(added!.id)
    store.undo()
    expect(store.blocks[2]!.title).toBe('Edited local')
    store.undo()
    expect(store.blocks[2]!.title).toBe('Local')
    store.undo()
    expect(store.blocks).toHaveLength(2)
    expect(store.isDirty).toBe(false)
    await store.updateBlockContent(1, { title: 'Different edit' })
    expect(store.canRedo).toBe(false)
  })

  it('keeps metadata in history and clears history only after a successful save', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    store.stageSession({ title: 'Changed', date: '2030-01-01', start_time: '18:00:00', end_time: '20:00:00' })
    store.undo()
    expect(store.session!.title).toBe('Plan')
    store.redo()
    api.savePlan.mockRejectedValue(new Error('offline'))
    await expect(store.savePendingMoves()).rejects.toThrow()
    expect(store.canUndo).toBe(true)
    api.savePlan.mockResolvedValue({ data: { ...plan(), revision: 2 } })
    await store.savePendingMoves()
    expect(store.canUndo).toBe(false)
    expect(store.canRedo).toBe(false)
  })

  it('a drag into an occupied period changes only the dragged block', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    store.stageMove(1, { start_offset_minutes: 5 })
    expect(store.blocks[1]!.start_offset_minutes).toBe(0)
  })

  it('stages station fields, instructors and materials and sends them as one complete plan', async () => {
    const store = useTrainingPlannerStore()
    await store.loadBlocks(1)
    await store.updateBlockContent(1, {
      kind: 'station', location: 'Hydrant Nord', learning_objective: 'Kuppeln', safety_notes: 'Handschuhe',
      instructors: [{ id: 7, name: 'Alex Ausbilder' }],
      materials: [{ item: 3, variant: null, quantity: 2, label: 'C-Schlauch' }, { item: null, variant: null, quantity: 1, label: 'Kreide' }],
    })
    expect(store.isDirty).toBe(true)
    expect(store.blocks[0]!.instructors).toEqual([{ id: 7, name: 'Alex Ausbilder' }])
    api.savePlan.mockResolvedValue({ data: { ...plan(), revision: 2 } })
    await store.savePendingMoves()
    const sent = api.savePlan.mock.calls[0]![1].blocks[0]
    expect(sent).toMatchObject({
      id: 1, kind: 'station', location: 'Hydrant Nord', learning_objective: 'Kuppeln', safety_notes: 'Handschuhe',
      instructor_ids: [7],
      materials: [{ item: 3, variant: null, quantity: 2, label: 'C-Schlauch' }, { item: null, variant: null, quantity: 1, label: 'Kreide' }],
    })
    expect(sent).not.toHaveProperty('instructors')
    store.undo()
  })
})
