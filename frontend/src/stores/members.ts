import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { membersApi, type MemberListParams, statusesApi, groupsApi, eventsApi, eventTypesApi } from '@/api/members'
import type { Member, Status, Group, Event, EventType, MemberCreate } from '@/types/api'

export const useMembersStore = defineStore('members', () => {
  // State
  const members = ref<Member[]>([])
  const currentMember = ref<Member | null>(null)
  const statuses = ref<Status[]>([])
  const groups = ref<Group[]>([])
  const events = ref<Event[]>([])
  const eventTypes = ref<EventType[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({
    count: 0,
    next: null as string | null,
    previous: null as string | null
  })

  // Computed
  const memberOptions = computed(() => 
    members.value.map(m => ({ 
      label: m.full_name, 
      value: m.id 
    }))
  )

  const statusOptions = computed(() => 
    statuses.value.map(s => ({ 
      label: s.name, 
      value: s.id,
      color: s.color
    }))
  )

  const groupOptions = computed(() => 
    groups.value.map(g => ({ 
      label: g.name, 
      value: g.id 
    }))
  )

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

  async function createMember(data: MemberCreate | FormData) {
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

  async function updateMember(id: number, data: Partial<MemberCreate> | FormData) {
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
      statuses.value = response.data.results || []
    } catch (err: any) {
      console.error('Failed to fetch statuses:', err)
      statuses.value = []
    }
  }

  async function fetchGroups() {
    try {
      const response = await groupsApi.list()
      groups.value = response.data.results || []
    } catch (err: any) {
      console.error('Failed to fetch groups:', err)
      groups.value = []
    }
  }

  async function fetchEvents(params?: { member?: number; type?: number; ordering?: string }) {
    try {
      const response = await eventsApi.list(params)
      events.value = response.data.results || []
    } catch (err: any) {
      console.error('Failed to fetch events:', err)
      events.value = []
    }
  }

  async function fetchEventTypes() {
    try {
      const response = await eventTypesApi.list()
      eventTypes.value = response.data.results || []
    } catch (err: any) {
      console.error('Failed to fetch event types:', err)
      eventTypes.value = []
    }
  }

  async function createEvent(data: Omit<Event, 'id' | 'member_name' | 'event_type'>) {
    loading.value = true
    error.value = null

    try {
      const response = await eventsApi.create(data)
      events.value.unshift(response.data)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to create event'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    members,
    currentMember,
    statuses,
    groups,
    events,
    eventTypes,
    loading,
    error,
    pagination,
    // Computed
    memberOptions,
    statusOptions,
    groupOptions,
    // Actions
    fetchMembers,
    fetchMemberById,
    createMember,
    updateMember,
    deleteMember,
    fetchStatuses,
    fetchGroups,
    fetchEvents,
    fetchEventTypes,
    createEvent,
    resetStore: () => {
      members.value = []
      currentMember.value = null
      statuses.value = []
      groups.value = []
      events.value = []
      eventTypes.value = []
      error.value = null
      pagination.value = {
        count: 0,
        next: null,
        previous: null
      }
    }
  }
})
