import { defineStore } from 'pinia'
import { ref } from 'vue'
import { memberListsApi } from '@/api/lists'
import { getApiErrorMessage } from '@/utils/apiError'
import { useDepartmentsStore } from '@/stores/departments'
import type {
  BulkAddResult,
  BulkCheckPreview,
  BulkCheckResult,
  CreateFromEventTypeParams,
  MemberList,
  MemberListCreate,
  MemberListDetail,
  MemberListEntry,
  MemberListEntryConflict,
  MemberListEntryState,
  MemberListUpdate,
} from '@/types/lists'
import type { Attachment } from '@/types/qualifications'

/** Someone else changed the entry first; `current` is the state now shown (UX-03.2). */
export class ListEntryConflictError extends Error {
  constructor(public readonly current: MemberListEntryState, public readonly memberName: string) {
    super('Der Eintrag wurde inzwischen geändert.')
    this.name = 'ListEntryConflictError'
  }
}

function conflictState(error: unknown): MemberListEntryState | null {
  const response = (error as { response?: { status?: number; data?: Partial<MemberListEntryConflict> } }).response
  return response?.status === 409 && response.data?.current ? response.data.current : null
}

function applyEntryState(entry: MemberListEntry, state: MemberListEntryState) {
  entry.checked = state.checked
  entry.checked_at = state.checked_at
  entry.notes = state.notes
  entry.version = state.version
}

export const useMemberListsStore = defineStore('memberLists', () => {
  // ── State ────────────────────────────────────────────────────────────────
  const lists = ref<MemberList[]>([])
  const currentList = ref<MemberListDetail | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const loadingAttachments = ref(false)
  const error = ref<string | null>(null)
  const listAttachments = ref<Record<number, Attachment[]>>({})

  // ── Lists CRUD ───────────────────────────────────────────────────────────
  async function fetchLists() {
    loading.value = true
    error.value = null
    try {
      const response = await memberListsApi.list()
      lists.value = response.data.results
      return lists.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden der Listen')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchList(id: number) {
    loading.value = true
    error.value = null
    try {
      const response = await memberListsApi.get(id)
      currentList.value = response.data
      // Keep the overview list in sync too
      const idx = lists.value.findIndex((l) => l.id === id)
      if (idx !== -1) {
        lists.value[idx] = { ...lists.value[idx], ...response.data }
      }
      return currentList.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden der Liste')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createList(data: MemberListCreate): Promise<MemberList> {
    saving.value = true
    try {
      const response = await memberListsApi.create(data)
      lists.value = [...lists.value, response.data].sort((a, b) => a.name.localeCompare(b.name))
      return response.data
    } finally {
      saving.value = false
    }
  }

  async function updateList(id: number, data: MemberListUpdate): Promise<MemberList> {
    saving.value = true
    try {
      const response = await memberListsApi.update(id, data)
      const idx = lists.value.findIndex((l) => l.id === id)
      if (idx !== -1) lists.value[idx] = { ...lists.value[idx], ...response.data }
      if (currentList.value?.id === id) {
        currentList.value = { ...currentList.value, ...response.data }
      }
      return response.data
    } finally {
      saving.value = false
    }
  }

  async function deleteList(id: number): Promise<void> {
    await memberListsApi.delete(id)
    lists.value = lists.value.filter((l) => l.id !== id)
    if (currentList.value?.id === id) currentList.value = null
  }

  // ── Membership management ────────────────────────────────────────────────
  async function addMember(listId: number, memberId: number): Promise<void> {
    await memberListsApi.addMember(listId, memberId)
    await fetchList(listId)
  }

  async function removeMember(listId: number, memberId: number): Promise<void> {
    if (currentList.value?.id === listId) {
      currentList.value = {
        ...currentList.value,
        entries: currentList.value.entries.filter((e) => e.member.id !== memberId),
      }
    }
    try {
      await memberListsApi.removeMember(listId, memberId)
    } catch (err) {
      // Refetch on failure
      await fetchList(listId)
      throw err
    }
    syncOverviewCount(listId)
  }

  async function previewBulkAdd(listId: number, memberIds: number[]): Promise<BulkAddResult> {
    return (await memberListsApi.bulkAdd(listId, memberIds, true)).data
  }

  async function bulkAdd(listId: number, memberIds: number[]): Promise<BulkAddResult> {
    const { data } = await memberListsApi.bulkAdd(listId, memberIds)
    await fetchList(listId)
    return data
  }

  // ── Check / uncheck ──────────────────────────────────────────────────────
  function findEntry(listId: number, memberId: number) {
    return currentList.value?.id === listId ? currentList.value.entries.find((e) => e.member.id === memberId) : undefined
  }

  /**
   * Sets one entry explicitly and sends the version the user saw. On a
   * conflict the current server state replaces the local one and a
   * `ListEntryConflictError` tells the view what happened.
   */
  async function setCheck(listId: number, memberId: number, checked: boolean): Promise<void> {
    const entry = findEntry(listId, memberId)
    if (!entry) return
    const previous = { checked: entry.checked, checked_at: entry.checked_at }
    entry.checked = checked
    entry.checked_at = checked ? new Date().toISOString() : null
    try {
      const { data } = await memberListsApi.setCheck(listId, memberId, checked, entry.version)
      applyEntryState(entry, data)
    } catch (err) {
      const current = conflictState(err)
      if (current) {
        applyEntryState(entry, current)
        throw new ListEntryConflictError(current, entry.member.full_name ?? '')
      }
      entry.checked = previous.checked
      entry.checked_at = previous.checked_at
      throw err
    } finally {
      syncCheckedCount(listId)
    }
  }

  async function previewBulkCheck(listId: number, checked: boolean): Promise<BulkCheckPreview> {
    return (await memberListsApi.previewBulkCheck(listId, checked)).data
  }

  /** Applies a previewed bulk change and takes over the server state of every entry. */
  async function applyBulkCheck(listId: number, checked: boolean, memberIds: number[]): Promise<BulkCheckResult> {
    const { data } = await memberListsApi.applyBulkCheck(listId, checked, memberIds)
    if (currentList.value?.id === listId) {
      const states = new Map(data.entries.map((state) => [state.member_id, state]))
      currentList.value.entries.forEach((entry) => {
        const state = states.get(entry.member.id)
        if (state) applyEntryState(entry, state)
      })
    }
    syncCheckedCount(listId)
    return data
  }

  async function updateEntryNotes(listId: number, memberId: number, notes: string): Promise<void> {
    const entry = findEntry(listId, memberId)
    try {
      const { data } = await memberListsApi.updateEntryNotes(listId, memberId, notes, entry?.version)
      if (entry) applyEntryState(entry, data)
    } catch (err) {
      const current = conflictState(err)
      if (current && entry) {
        applyEntryState(entry, current)
        syncCheckedCount(listId)
        throw new ListEntryConflictError(current, entry.member.full_name ?? '')
      }
      throw err
    }
  }

  // ── Attachments ──────────────────────────────────────────────────────────
  async function fetchListAttachments(listId: number): Promise<Attachment[]> {
    loadingAttachments.value = true
    try {
      const response = await memberListsApi.attachments.list(listId)
      listAttachments.value[listId] = response.data
      return response.data
    } finally {
      loadingAttachments.value = false
    }
  }

  async function uploadListAttachment(listId: number, data: FormData): Promise<Attachment> {
    loadingAttachments.value = true
    try {
      const response = await memberListsApi.attachments.upload(listId, data)
      const existing = listAttachments.value[listId] ?? []
      listAttachments.value[listId] = [response.data, ...existing]
      return response.data
    } finally {
      loadingAttachments.value = false
    }
  }

  async function deleteListAttachment(listId: number, attachmentId: number): Promise<void> {
    loadingAttachments.value = true
    try {
      await memberListsApi.attachments.delete(listId, attachmentId)
      const existing = listAttachments.value[listId] ?? []
      listAttachments.value[listId] = existing.filter((a) => a.id !== attachmentId)
    } finally {
      loadingAttachments.value = false
    }
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  async function exportExcel(listId: number, columns?: string[]) {
    loading.value = true
    try {
      const response = await memberListsApi.exportExcel(listId, columns)
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      const disposition = response.headers['content-disposition'] ?? ''
      const match = disposition.match(/filename="([^"]+)"/)
      link.download = match ? match[1] : `liste_${listId}.xlsx`
      link.click()
      window.URL.revokeObjectURL(url)
    } finally {
      loading.value = false
    }
  }

  function syncCheckedCount(listId: number) {
    const idx = lists.value.findIndex((l) => l.id === listId)
    const list = lists.value[idx]
    if (list && currentList.value?.id === listId) {
      list.checked_count = currentList.value.entries.filter((e) => e.checked).length
    }
  }

  function syncOverviewCount(listId: number) {
    const idx = lists.value.findIndex((l) => l.id === listId)
    const list = lists.value[idx]
    if (list && currentList.value?.id === listId) {
      list.member_count = currentList.value.entries.length
    }
  }

  async function createFromEventType(params: CreateFromEventTypeParams): Promise<MemberList> {
    saving.value = true
    const departmentsStore = useDepartmentsStore()
    const activeDeptId = departmentsStore.activeDepartmentId
    try {
      // The body names the owner explicitly; null creates an organization-wide list.
      const response = await memberListsApi.createFromEventType({ ...params, department: activeDeptId ?? null }, activeDeptId)
      lists.value = [...lists.value, response.data].sort((a, b) => a.name.localeCompare(b.name))
      return response.data
    } finally {
      saving.value = false
    }
  }

  return {
    lists,
    currentList,
    loading,
    saving,
    loadingAttachments,
    error,
    listAttachments,
    fetchLists,
    fetchList,
    createList,
    updateList,
    deleteList,
    addMember,
    removeMember,
    previewBulkAdd,
    bulkAdd,
    setCheck,
    previewBulkCheck,
    applyBulkCheck,
    updateEntryNotes,
    fetchListAttachments,
    uploadListAttachment,
    deleteListAttachment,
    exportExcel,
    createFromEventType,
  }
})
