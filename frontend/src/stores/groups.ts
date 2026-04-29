/**
 * Pinia store for member groups
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { groupsApi, membersApi } from '@/api/members'
import { getApiErrorMessage } from '@/utils/apiError'
import type { Group, Member } from '@/types/members'

export type { Group }

export const useGroupsStore = defineStore('groups', () => {
  // State
  const groups = ref<Group[]>([])
  const members = ref<Member[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  // Actions
  async function fetchGroups() {
    loading.value = true
    error.value = null
    try {
      const response = await groupsApi.list()
      groups.value = response.data.results
      return groups.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden der Gruppen')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchAllMembers() {
    const response = await membersApi.list({ limit: 1000, ordering: 'lastname,name' })
    members.value = response.data.results
    return members.value
  }

  async function createGroup(name: string): Promise<Group> {
    saving.value = true
    try {
      const response = await groupsApi.create({ name })
      groups.value = [...groups.value, response.data].sort((a, b) => a.name.localeCompare(b.name))
      return response.data
    } finally {
      saving.value = false
    }
  }

  async function updateGroup(id: number, name: string): Promise<Group> {
    saving.value = true
    try {
      const response = await groupsApi.update(id, { name })
      const idx = groups.value.findIndex((g) => g.id === id)
      if (idx !== -1) groups.value[idx] = response.data
      return response.data
    } finally {
      saving.value = false
    }
  }

  async function deleteGroup(id: number): Promise<void> {
    await groupsApi.delete(id)
    groups.value = groups.value.filter((g) => g.id !== id)
    // Clear group reference on any member that had this group
    members.value.forEach((m) => {
      if (m.group?.id === id) m.group = null
    })
  }

  async function assignMember(memberId: number, groupId: number | null): Promise<void> {
    // Optimistic update
    const member = members.value.find((m) => m.id === memberId)
    const previousGroup = member?.group ?? null
    if (member) {
      member.group = groupId ? (groups.value.find((g) => g.id === groupId) ?? null) : null
    }
    try {
      await membersApi.update(memberId, { group: groupId })
    } catch (err) {
      // Rollback on failure
      if (member) member.group = previousGroup
      throw err
    }
  }

  return {
    groups,
    members,
    loading,
    saving,
    error,
    fetchGroups,
    fetchAllMembers,
    createGroup,
    updateGroup,
    deleteGroup,
    assignMember,
  }
})
