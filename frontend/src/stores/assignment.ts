import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { participationApi, type AssignmentBoard, type BoardApplicant, type DraftTarget } from '@/api/participation'
import { getApiErrorMessage } from '@/utils/apiError'

export const ASSIGNMENT_STALE = 'Die Zuteilung wurde inzwischen von jemand anderem geändert.'

export type SortKey = 'applied' | 'name' | 'fairness'

interface ErrorBody { code?: string, detail?: string, reasons?: string[], current?: AssignmentBoard }
const responseOf = (err: unknown) => (err as { response?: { status?: number, data?: ErrorBody } }).response

/** Can `person` take `target` in `draft`? Returns a reason when not (shown while dragging). */
export function blockReason(board: AssignmentBoard, draft: Record<string, DraftTarget>, person: BoardApplicant, target: DraftTarget): string | null {
  const taken = Object.entries(draft).filter(([id, value]) => value === target && Number(id) !== person.member_id).length
  if (target === 'extra') {
    if (!person.general_ok) return person.general_reasons.join('; ') || 'Allgemeine Voraussetzungen nicht erfüllt'
    if (taken >= (board.extra_places ?? 0)) return 'Keine Plätze ohne Position frei'
    return null
  }
  const slot = board.slots.find(s => s.id === target)
  if (!slot) return 'Unbekannte Position'
  if (!person.fits.includes(target)) return (person.reasons[String(target)] ?? []).join('; ') || 'Passt nicht zu dieser Position'
  if (taken >= slot.max) return 'Alle Plätze dieser Position sind belegt'
  return null
}

export const useAssignmentStore = defineStore('assignment', () => {
  const sessionId = ref<number | null>(null)
  const board = ref<AssignmentBoard | null>(null)
  const draft = ref<Record<string, DraftTarget>>({})
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const reasons = ref<string[]>([])
  const conflict = ref<AssignmentBoard | null>(null)
  const notice = ref<string | null>(null)
  const sort = ref<SortKey>('applied')
  const onlyFor = ref<number | 'all'>('all')

  const dirty = computed(() => !!board.value && JSON.stringify(sorted(draft.value)) !== JSON.stringify(sorted(board.value.draft)))
  /** Draft differs from what the applicants were told. */
  const unpublished = computed(() => {
    if (!board.value) return false
    const published: Record<string, DraftTarget> = {}
    for (const a of board.value.applicants) if (a.published !== null) published[a.member_id] = a.published
    return JSON.stringify(sorted(draft.value)) !== JSON.stringify(sorted(published))
  })

  function sorted(map: Record<string, DraftTarget>) {
    return Object.keys(map).sort().map(key => [key, map[key]])
  }

  const unassigned = computed(() => {
    const list = (board.value?.applicants ?? []).filter(a => draft.value[a.member_id] === undefined)
    const filtered = onlyFor.value === 'all' ? list : list.filter(a => a.fits.includes(onlyFor.value as number))
    const byName = (a: BoardApplicant, b: BoardApplicant) => `${a.lastname} ${a.name}`.localeCompare(`${b.lastname} ${b.name}`, 'de')
    return [...filtered].sort((a, b) => {
      if (sort.value === 'name') return byName(a, b)
      if (sort.value === 'fairness') return a.recent_assignments - b.recent_assignments || byName(a, b)
      return a.applied_at.localeCompare(b.applied_at)
    })
  })

  function inTarget(target: DraftTarget) {
    return (board.value?.applicants ?? []).filter(a => draft.value[a.member_id] === target)
  }

  function adopt(next: AssignmentBoard, keepDraft = false) {
    board.value = next
    if (!keepDraft) draft.value = { ...next.draft }
  }

  async function load(id: number) {
    if (sessionId.value !== id) { board.value = null; draft.value = {}; conflict.value = null }
    sessionId.value = id
    loading.value = true
    error.value = null
    try {
      adopt((await participationApi.assignment(id)).data)
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Die Zuteilung konnte nicht geladen werden.')
    } finally {
      loading.value = false
    }
  }

  /** Assign `memberId` to `target` (or back to the applications with null). */
  function assign(memberId: number, target: DraftTarget | null): string | null {
    if (!board.value) return null
    const person = board.value.applicants.find(a => a.member_id === memberId)
    if (!person) return null
    if (target === null) {
      const next = { ...draft.value }
      delete next[memberId]
      draft.value = next
      notice.value = `${person.name} ${person.lastname} zurück zu den Bewerbungen.`
      return null
    }
    const reason = blockReason(board.value, draft.value, person, target)
    if (reason) { notice.value = reason; return reason }
    draft.value = { ...draft.value, [memberId]: target }
    const label = target === 'extra' ? 'ohne Position' : board.value.slots.find(s => s.id === target)?.label
    notice.value = `${person.name} ${person.lastname} zugeteilt: ${label}.`
    return null
  }

  function handleError(err: unknown, fallback: string) {
    const response = responseOf(err)
    if (response?.status === 409) {
      conflict.value = response.data?.current ?? null
      error.value = ASSIGNMENT_STALE
      return
    }
    reasons.value = response?.data?.reasons ?? []
    error.value = getApiErrorMessage(err, fallback)
  }

  async function save(): Promise<boolean> {
    if (!board.value || sessionId.value === null) return false
    saving.value = true
    error.value = null
    reasons.value = []
    try {
      adopt((await participationApi.saveAssignment(sessionId.value, { revision: board.value.revision, draft: draft.value })).data)
      notice.value = 'Entwurf gespeichert.'
      return true
    } catch (err) {
      handleError(err, 'Der Entwurf konnte nicht gespeichert werden.')
      return false
    } finally {
      saving.value = false
    }
  }

  async function publish(keepOpen: boolean): Promise<boolean> {
    if (!board.value || sessionId.value === null) return false
    if (dirty.value && !(await save())) return false
    saving.value = true
    error.value = null
    try {
      adopt((await participationApi.publishAssignment(sessionId.value, { revision: board.value!.revision, keep_open: keepOpen })).data)
      notice.value = 'Zuteilung veröffentlicht. Alle Bewerbenden werden benachrichtigt.'
      return true
    } catch (err) {
      handleError(err, 'Die Zuteilung konnte nicht veröffentlicht werden.')
      return false
    } finally {
      saving.value = false
    }
  }

  function useServerVersion() {
    if (conflict.value) adopt(conflict.value)
    conflict.value = null
    error.value = null
  }

  function keepDraftOnServerVersion() {
    if (conflict.value) adopt(conflict.value, true)
    conflict.value = null
    error.value = null
  }

  return {
    sessionId, board, draft, loading, saving, error, reasons, conflict, notice, sort, onlyFor, dirty, unpublished, unassigned,
    inTarget, load, assign, save, publish, useServerVersion, keepDraftOnServerVersion,
  }
})
