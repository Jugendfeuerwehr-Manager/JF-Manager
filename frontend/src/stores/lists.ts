import { defineStore } from 'pinia'
import { ref } from 'vue'
import { memberListsApi } from '@/api/lists'
import { getApiErrorMessage } from '@/utils/apiError'
import { useDepartmentsStore } from '@/stores/departments'
import type { MemberList, MemberListCreate, MemberListDetail, MemberListUpdate, CreateFromEventTypeParams } from '@/types/lists'
import type { Attachment } from '@/types/qualifications'

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

  async function bulkAdd(listId: number, memberIds: number[]): Promise<void> {
    await memberListsApi.bulkAdd(listId, memberIds)
    await fetchList(listId)
  }

  // ── Check / uncheck ──────────────────────────────────────────────────────
  async function toggleCheck(listId: number, memberId: number): Promise<void> {
    if (currentList.value?.id !== listId) return
    // Optimistic update
    const entry = currentList.value.entries.find((e) => e.member.id === memberId)
    if (entry) {
      entry.checked = !entry.checked
      entry.checked_at = entry.checked ? new Date().toISOString() : null
    }
    try {
      const res = await memberListsApi.toggleCheck(listId, memberId)
      if (entry) {
        entry.checked = res.data.checked
        entry.checked_at = res.data.checked_at
      }
    } catch (err) {
      // Rollback
      if (entry) {
        entry.checked = !entry.checked
        entry.checked_at = null
      }
      throw err
    }
    syncCheckedCount(listId)
  }

  async function checkAll(listId: number): Promise<void> {
    await memberListsApi.checkAll(listId)
    if (currentList.value?.id === listId) {
      const now = new Date().toISOString()
      currentList.value.entries.forEach((e) => { e.checked = true; e.checked_at = now })
    }
    syncCheckedCount(listId)
  }

  async function uncheckAll(listId: number): Promise<void> {
    await memberListsApi.uncheckAll(listId)
    if (currentList.value?.id === listId) {
      currentList.value.entries.forEach((e) => { e.checked = false; e.checked_at = null })
    }
    syncCheckedCount(listId)
  }

  async function updateEntryNotes(listId: number, memberId: number, notes: string): Promise<void> {
    await memberListsApi.updateEntryNotes(listId, memberId, notes)
    if (currentList.value?.id === listId) {
      const entry = currentList.value.entries.find((e) => e.member.id === memberId)
      if (entry) entry.notes = notes
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

  function syncCheckedCount(listId: number) {    const idx = lists.value.findIndex((l) => l.id === listId)
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
      const response = await memberListsApi.createFromEventType(params, activeDeptId)
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
    bulkAdd,
    toggleCheck,
    checkAll,
    uncheckAll,
    updateEntryNotes,
    fetchListAttachments,
    uploadListAttachment,
    deleteListAttachment,
    exportExcel,
    createFromEventType,
  }
})
