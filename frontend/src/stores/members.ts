import { defineStore } from 'pinia'
import { ref } from 'vue'
import { membersApi, type MemberListParams, statusesApi, groupsApi } from '@/api/members'
import type { Member, Status, Group } from '@/types/api'

export const useMembersStore = defineStore('members', () => {
  // State
  const members = ref<Member[]>([])
  const currentMember = ref<Member | null>(null)
  const statuses = ref<Status[]>([])
  const groups = ref<Group[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({
    count: 0,
    next: null as string | null,
    previous: null as string | null
  })

  // Actions
  async function fetchMembers(params?: MemberListParams) {
    loading.value = true
    error.value = null
    try {
      const response = await membersApi.list(params)
      members.value = response.data.results
      pagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous
      }
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch members'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchMemberById(id: number) {
    loading.value = true
    error.value = null

    try {
      const response = await membersApi.get(id)
      currentMember.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch member'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createMember(data: any) {
    loading.value = true
    error.value = null

    try {
      const response = await membersApi.create(data)
      members.value.unshift(response.data)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to create member'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateMember(id: number, data: any) {
    loading.value = true
    error.value = null

    try {
      const response = await membersApi.update(id, data)
      const index = members.value.findIndex((m) => m.id === id)
      if (index !== -1) {
        members.value[index] = response.data
      }
      if (currentMember.value?.id === id) {
        currentMember.value = response.data
      }
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to update member'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteMember(id: number) {
    loading.value = true
    error.value = null

    try {
      await membersApi.delete(id)
      members.value = members.value.filter((m) => m.id !== id)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to delete member'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchStatuses() {
    try {
      const response = await statusesApi.list()
      statuses.value = Array.isArray(response.data.results) ? response.data.results : []
    } catch (err: any) {
      console.error('Failed to fetch statuses:', err)
      statuses.value = []
    }
  }

  async function fetchGroups() {
    try {
      const response = await groupsApi.list()
      groups.value = Array.isArray(response.data.results) ? response.data.results : []
    } catch (err: any) {
      console.error('Failed to fetch groups:', err)
      groups.value = []
    }
  }

  return {
    // State
    members,
    currentMember,
    statuses,
    groups,
    loading,
    error,
    pagination,
    // Actions
    fetchMembers,
    fetchMemberById,
    createMember,
    updateMember,
    deleteMember,
    fetchStatuses,
    fetchGroups
    ,
    resetStore: () => {
      members.value = []
      currentMember.value = null
      statuses.value = []
      groups.value = []
      error.value = null
      pagination.value = {
        count: 0,
        next: null,
        previous: null
      }
    }
  }
})
