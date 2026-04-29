import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { trainingBlocksApi } from '@/api/training'
import type { PlannerBlock, TrainingBlock, TrainingBlockCreate, TrainingBlockMove } from '@/types/training'

export const useTrainingPlannerStore = defineStore('trainingPlanner', () => {
  // ── State ────────────────────────────────────────────────────────────────
  const sessionId = ref<number | null>(null)
  const blocks = ref<PlannerBlock[]>([])
  const selectedBlockId = ref<number | null>(null)
  const draggingBlockId = ref<number | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  /** Tracks unsaved position/duration changes for batch save. */
  const pendingMoves = ref<Map<number, TrainingBlockMove>>(new Map())

  // ── Getters ──────────────────────────────────────────────────────────────
  const isDirty = computed(() => pendingMoves.value.size > 0)
  const selectedBlock = computed(() =>
    blocks.value.find((b) => b.id === selectedBlockId.value) ?? null
  )

  function blocksByGroup(groupId: number | null): PlannerBlock[] {
    if (groupId === null) {
      // All-group blocks (empty groups array)
      return blocks.value.filter((b) => b.allGroups)
    }
    return blocks.value.filter(
      (b) => !b.allGroups && b.groupIds.includes(groupId)
    )
  }

  // ── Actions ──────────────────────────────────────────────────────────────
  async function loadBlocks(sid: number) {
    sessionId.value = sid
    loading.value = true
    error.value = null
    try {
      const response = await trainingBlocksApi.list({ session: sid, limit: 1000 })
      blocks.value = response.data.results.map(normalizeToPlannerBlock)
      pendingMoves.value.clear()
    } catch (e: unknown) {
      error.value = 'Fehler beim Laden der Blöcke'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function addBlock(data: TrainingBlockCreate) {
    saving.value = true
    error.value = null
    try {
      const response = await trainingBlocksApi.create(data)
      blocks.value = [...blocks.value, normalizeToPlannerBlock(response.data)]
      return response.data
    } catch (e: unknown) {
      error.value = 'Fehler beim Hinzufügen des Blocks'
      throw e
    } finally {
      saving.value = false
    }
  }

  async function updateBlockContent(id: number, data: Partial<TrainingBlockCreate>) {
    saving.value = true
    error.value = null
    try {
      const response = await trainingBlocksApi.update(id, data)
      const idx = blocks.value.findIndex((b) => b.id === id)
      if (idx !== -1) {
        blocks.value[idx] = normalizeToPlannerBlock(response.data)
      }
      return response.data
    } catch (e: unknown) {
      error.value = 'Fehler beim Speichern des Blocks'
      throw e
    } finally {
      saving.value = false
    }
  }

  /**
   * Stage a position change locally (during drag/resize).
   * Does NOT save to backend — call savePendingMoves() afterwards.
   */
  function stageMove(id: number, move: TrainingBlockMove) {
    const block = blocks.value.find((b) => b.id === id)
    if (!block) return

    // Apply optimistically
    if (move.start_offset_minutes !== undefined) block.start_offset_minutes = move.start_offset_minutes
    if (move.duration_minutes !== undefined) block.duration_minutes = move.duration_minutes
    if (move.position_order !== undefined) block.position_order = move.position_order
    if (move.groups !== undefined) {
      block.groupIds = move.groups
      block.allGroups = move.groups.length === 0
    }

    // Merge into pending
    const existing = pendingMoves.value.get(id) ?? {}
    pendingMoves.value.set(id, { ...existing, ...move })
  }

  /** Save all staged moves to the backend in parallel. */
  async function savePendingMoves() {
    if (pendingMoves.value.size === 0) return
    saving.value = true
    error.value = null
    const moves = new Map(pendingMoves.value)
    pendingMoves.value.clear()
    try {
      await Promise.all(
        Array.from(moves.entries()).map(([id, move]) =>
          trainingBlocksApi.move(id, move)
        )
      )
    } catch (e: unknown) {
      error.value = 'Fehler beim Speichern der Positionen'
      // Re-stage failed moves
      moves.forEach((move, id) => pendingMoves.value.set(id, move))
      throw e
    } finally {
      saving.value = false
    }
  }

  async function removeBlock(id: number) {
    loading.value = true
    error.value = null
    try {
      await trainingBlocksApi.delete(id)
      blocks.value = blocks.value.filter((b) => b.id !== id)
      pendingMoves.value.delete(id)
      if (selectedBlockId.value === id) selectedBlockId.value = null
    } catch (e: unknown) {
      error.value = 'Fehler beim Löschen des Blocks'
      throw e
    } finally {
      loading.value = false
    }
  }

  function selectBlock(id: number | null) {
    selectedBlockId.value = id
  }

  function setDragging(id: number | null) {
    draggingBlockId.value = id
  }

  function reset() {
    sessionId.value = null
    blocks.value = []
    selectedBlockId.value = null
    draggingBlockId.value = null
    pendingMoves.value.clear()
    error.value = null
  }

  // ── Helpers ──────────────────────────────────────────────────────────────
  function normalizeToPlannerBlock(b: TrainingBlock): PlannerBlock {
    return {
      ...b,
      groupIds: b.groups.map((g) => g.id),
      allGroups: b.groups.length === 0,
    }
  }

  return {
    sessionId,
    blocks,
    selectedBlockId,
    draggingBlockId,
    pendingMoves,
    loading,
    saving,
    error,
    isDirty,
    selectedBlock,
    blocksByGroup,
    loadBlocks,
    addBlock,
    updateBlockContent,
    stageMove,
    savePendingMoves,
    removeBlock,
    selectBlock,
    setDragging,
    reset,
  }
})
