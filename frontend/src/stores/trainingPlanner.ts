import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { libraryApi, trainingSessionsApi } from '@/api/training'
import type {
  GroupMini, PlannerBlock, TrainingBlock, TrainingBlockCreate, TrainingBlockMove,
  TrainingPlanDraft, TrainingSessionCreate, TrainingSessionDetail,
} from '@/types/training'

interface DraftSnapshot {
  session: TrainingSessionDetail | null
  blocks: PlannerBlock[]
  moves: Array<[number, TrainingBlockMove]>
}

export const useTrainingPlannerStore = defineStore('trainingPlanner', () => {
  const sessionId = ref<number | null>(null)
  const session = ref<TrainingSessionDetail | null>(null)
  const blocks = ref<PlannerBlock[]>([])
  const selectedBlockId = ref<number | null>(null)
  const draggingBlockId = ref<number | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const conflict = ref<TrainingSessionDetail | null>(null)
  const pendingMoves = ref<Map<number, TrainingBlockMove>>(new Map())
  const baseline = ref('')
  let nextLocalId = -1
  let generation = 0
  const past = ref<DraftSnapshot[]>([])
  const future = ref<DraftSnapshot[]>([])
  let gestureStart: DraftSnapshot | null = null
  const canUndo = computed(() => past.value.length > 0 && !saving.value && !loading.value)
  const canRedo = computed(() => future.value.length > 0 && !saving.value && !loading.value)

  function snapshot(): DraftSnapshot {
    return JSON.parse(JSON.stringify({ session: session.value, blocks: blocks.value,
      moves: Array.from(pendingMoves.value.entries()) }))
  }

  function restore(value: DraftSnapshot) {
    const copy: DraftSnapshot = JSON.parse(JSON.stringify(value))
    session.value = copy.session
    blocks.value = copy.blocks
    pendingMoves.value = new Map(copy.moves)
    if (!blocks.value.some((b) => b.id === selectedBlockId.value)) selectedBlockId.value = null
  }

  function remember(previous: DraftSnapshot) {
    // A pointer gesture can contain hundreds of updates but is one undo step.
    if (JSON.stringify(previous) === JSON.stringify(snapshot())) return
    past.value = [...past.value.slice(-49), previous]
    future.value = []
  }

  function mutate(action: () => void) {
    const previous = gestureStart ? null : snapshot()
    action()
    if (previous) remember(previous)
  }

  function beginGesture() {
    if (!saving.value && !loading.value && !gestureStart) gestureStart = snapshot()
  }

  function endGesture() {
    if (gestureStart) remember(gestureStart)
    gestureStart = null
  }

  function undo() {
    if (!canUndo.value) return
    endGesture()
    const previous = past.value.pop()!
    future.value.push(snapshot())
    restore(previous)
  }

  function redo() {
    if (!canRedo.value) return
    const next = future.value.pop()!
    past.value.push(snapshot())
    restore(next)
  }

  const isDirty = computed(() => !!session.value && JSON.stringify(draft()) !== baseline.value)
  const selectedBlock = computed(() => blocks.value.find((b) => b.id === selectedBlockId.value) ?? null)

  function normalize(b: TrainingBlock): PlannerBlock {
    const groups = b.groups ?? []
    return { ...b, groups, groupIds: groups.map((g) => g.id), allGroups: groups.length === 0 }
  }

  function metadata(): TrainingSessionCreate {
    const s = session.value!
    return {
      title: s.title, description: s.description, date: s.date,
      start_time: s.start_time, end_time: s.end_time, location: s.location,
      notes: s.notes, department: s.department, group_ids: s.groups.map((g) => g.id),
      recurrence_rule: s.recurrence_rule,
    }
  }

  function draft(): TrainingPlanDraft {
    return {
      expected_revision: session.value?.revision ?? 1,
      session: session.value ? metadata() : {} as TrainingSessionCreate,
      blocks: blocks.value.map((b) => ({
        ...(b.id > 0 ? { id: b.id } : {}), session: b.session,
        title: b.title, content: b.content, group_ids: b.groupIds,
        library_block: b.library_block, duration_minutes: b.duration_minutes,
        start_offset_minutes: b.start_offset_minutes, position_order: b.position_order,
        color: b.color, nextcloud_folder_url: b.nextcloud_folder_url,
      })),
    }
  }

  function accept(data: TrainingSessionDetail) {
    session.value = data
    sessionId.value = data.id
    blocks.value = data.blocks.map(normalize)
    baseline.value = JSON.stringify(draft())
    pendingMoves.value.clear()
    conflict.value = null
    error.value = null
    selectedBlockId.value = null
    past.value = []
    future.value = []
    gestureStart = null
  }

  function assertEditable() {
    if (!session.value || loading.value || saving.value) throw new Error('Der Plan wird gerade geladen oder gespeichert.')
  }

  function groupsFor(ids: number[], choices: GroupMini[] = []): GroupMini[] {
    const known = [...(session.value?.groups ?? []), ...blocks.value.flatMap((b) => b.groups), ...choices]
    return ids.map((id) => known.find((g) => g.id === id) ?? { id, name: `Gruppe ${id}` })
  }

  function blocksByGroup(groupId: number | null): PlannerBlock[] {
    return blocks.value.filter((b) => groupId === null ? b.allGroups : !b.allGroups && b.groupIds.includes(groupId))
  }

  async function loadBlocks(sid: number) {
    const requestGeneration = ++generation
    loading.value = true
    error.value = null
    try {
      const response = await trainingSessionsApi.plan(sid)
      if (requestGeneration === generation) accept(response.data)
    } catch (e) {
      if (requestGeneration === generation) error.value = 'Fehler beim Laden des Plans'
      throw e
    } finally {
      if (requestGeneration === generation) loading.value = false
    }
  }

  async function addBlock(data: TrainingBlockCreate) {
    assertEditable()
    const requestGeneration = generation
    let content = data.content ?? ''
    let color = data.color ?? ''
    if (data.library_block && !content) {
      const source = await libraryApi.get(data.library_block)
      content = source.data.content
      color ||= source.data.color
    }
    if (requestGeneration !== generation) return
    assertEditable()
    const b: TrainingBlock = {
      id: nextLocalId--, session: sessionId.value!, title: data.title, content,
      groups: groupsFor(data.group_ids ?? []), library_block: data.library_block ?? null,
      library_block_title: null, duration_minutes: data.duration_minutes ?? 15,
      start_offset_minutes: data.start_offset_minutes ?? 0, position_order: data.position_order ?? 0,
      color, nextcloud_folder_url: data.nextcloud_folder_url ?? '',
      created_at: '', updated_at: '', media: [], attachments: [],
    }
    mutate(() => { blocks.value.push(normalize(b)) })
    return b
  }

  async function updateBlockContent(id: number, data: Partial<TrainingBlockCreate>) {
    assertEditable()
    const b = blocks.value.find((b) => b.id === id)
    if (!b) return
    const { group_ids, session: _targetSession, ...content } = data
    mutate(() => {
      Object.assign(b, content)
      if (group_ids) {
        b.groups = groupsFor(group_ids)
        b.groupIds = group_ids
        b.allGroups = group_ids.length === 0
      }
    })
    return b
  }

  function stageSession(data: TrainingSessionCreate, choices: GroupMini[] = []) {
    assertEditable()
    const { group_ids, ...values } = data
    mutate(() => {
      Object.assign(session.value!, values)
      if (group_ids) session.value!.groups = groupsFor(group_ids, choices)
    })
  }

  function stageMove(id: number, move: TrainingBlockMove) {
    if (saving.value || loading.value) return
    const b = blocks.value.find((b) => b.id === id)
    if (!b) return
    mutate(() => {
      if (move.start_offset_minutes !== undefined) b.start_offset_minutes = move.start_offset_minutes
      if (move.duration_minutes !== undefined) b.duration_minutes = move.duration_minutes
      if (move.position_order !== undefined) b.position_order = move.position_order
      if (move.groups !== undefined) {
        b.groups = groupsFor(move.groups)
        b.groupIds = move.groups
        b.allGroups = move.groups.length === 0
      }
      pendingMoves.value.set(id, { ...pendingMoves.value.get(id), ...move })
    })
  }

  async function savePendingMoves() {
    if (!isDirty.value || saving.value || loading.value || !sessionId.value) return
    const requestGeneration = generation
    const payload = draft()
    saving.value = true
    error.value = null
    try {
      const response = await trainingSessionsApi.savePlan(sessionId.value, payload)
      if (requestGeneration === generation) accept(response.data)
    } catch (e: unknown) {
      if (requestGeneration === generation) {
        const response = (e as { response?: { status: number; data?: { current?: TrainingSessionDetail; [key: string]: unknown } } }).response
        if (response?.status === 409 && response.data?.current) {
          conflict.value = response.data.current
          error.value = 'Der Serverplan wurde geändert. Dein Entwurf bleibt erhalten.'
        } else {
          const messages = (value: unknown): string[] => typeof value === 'string' ? [value]
            : value && typeof value === 'object' ? Object.values(value).flatMap(messages) : []
          const detail = response?.status === 400 ? messages(response.data).slice(0, 8).join(' ') : ''
          error.value = detail ? `Plan nicht gespeichert: ${detail}`
            : 'Plan nicht gespeichert. Bitte Verbindung und Berechtigung prüfen und erneut versuchen.'
        }
      }
      throw e
    } finally {
      if (requestGeneration === generation) saving.value = false
    }
  }

  async function removeBlock(id: number) {
    assertEditable()
    mutate(() => {
      blocks.value = blocks.value.filter((b) => b.id !== id)
      pendingMoves.value.delete(id)
      if (selectedBlockId.value === id) selectedBlockId.value = null
    })
  }

  function discardForServerVersion() {
    if (conflict.value && !saving.value) accept(conflict.value)
  }

  function selectBlock(id: number | null) { selectedBlockId.value = id }
  function setDragging(id: number | null) { draggingBlockId.value = id }

  function reset() {
    generation++
    sessionId.value = null
    session.value = null
    blocks.value = []
    baseline.value = ''
    selectedBlockId.value = null
    draggingBlockId.value = null
    pendingMoves.value.clear()
    conflict.value = null
    error.value = null
    loading.value = false
    saving.value = false
    past.value = []
    future.value = []
    gestureStart = null
  }

  return {
    sessionId, session, blocks, selectedBlockId, draggingBlockId, pendingMoves,
    loading, saving, error, conflict, isDirty, selectedBlock, blocksByGroup,
    canUndo, canRedo, undo, redo, beginGesture, endGesture,
    loadBlocks, addBlock, updateBlockContent, stageSession, stageMove, savePendingMoves,
    removeBlock, discardForServerVersion, selectBlock, setDragging, reset,
  }
})
