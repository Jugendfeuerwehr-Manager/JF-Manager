import apiClient from './index'
import type {
  Member,
  MemberCreate,
  Parent,
  Status,
  Group,
  Event,
  EventType,
  PaginatedResponse
} from '@/types/api'

// Re-export commonly used types so other modules can import them from this file
export type { Member, MemberCreate, Parent, Status, Group, Event, EventType, PaginatedResponse }

// Backwards-compatible alias for parameter type naming used in some stores
export type MemberParams = MemberListParams

export interface MemberListParams {
  limit?: number
  offset?: number
  search?: string
  status?: number
  group?: number
  ordering?: string
}

export const membersApi = {
  list(params?: MemberListParams) {
    return apiClient.get<PaginatedResponse<Member>>('/members/', { params })
  },

  get(id: number) {
    return apiClient.get<Member>(`/members/${id}/`)
  },

  create(data: MemberCreate) {
    return apiClient.post<Member>('/members/', data)
  },

  update(id: number, data: Partial<MemberCreate>) {
    return apiClient.patch<Member>(`/members/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/members/${id}/`)
  },

  getStatistics() {
    return apiClient.get<{ total: number; by_status: Record<string, number> }>('/members/statistics/')
  },

  getParents(id: number) {
    return apiClient.get<Parent[]>(`/members/${id}/parents/`)
  },

  getEvents(id: number) {
    return apiClient.get<Event[]>(`/members/${id}/events/`)
  }
}

export const parentsApi = {
  list(params?: MemberListParams) {
    return apiClient.get<PaginatedResponse<Parent>>('/parents/', { params })
  },

  get(id: number) {
    return apiClient.get<Parent>(`/parents/${id}/`)
  },

  create(data: Partial<Parent>) {
    return apiClient.post<Parent>('/parents/', data)
  },

  update(id: number, data: Partial<Parent>) {
    return apiClient.patch<Parent>(`/parents/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/parents/${id}/`)
  }
}

// Provide legacy method names some stores expect
;(parentsApi as any).getAll = function (params?: MemberListParams) {
  return parentsApi.list(params)
}

;(parentsApi as any).getById = function (id: number) {
  return parentsApi.get(id)
}

export const statusesApi = {
  list() {
    return apiClient.get<Status[]>('/statuses/')
  },

  get(id: number) {
    return apiClient.get<Status>(`/statuses/${id}/`)
  },

  create(data: Omit<Status, 'id'>) {
    return apiClient.post<Status>('/statuses/', data)
  },

  update(id: number, data: Partial<Omit<Status, 'id'>>) {
    return apiClient.patch<Status>(`/statuses/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/statuses/${id}/`)
  }
}

export const groupsApi = {
  list() {
    return apiClient.get<Group[]>('/groups/')
  },

  get(id: number) {
    return apiClient.get<Group>(`/groups/${id}/`)
  },

  create(data: Omit<Group, 'id'>) {
    return apiClient.post<Group>('/groups/', data)
  },

  update(id: number, data: Partial<Omit<Group, 'id'>>) {
    return apiClient.patch<Group>(`/groups/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/groups/${id}/`)
  }
}

export const eventsApi = {
  list(params?: { member?: number; type?: number; ordering?: string }) {
    return apiClient.get<PaginatedResponse<Event>>('/events/', { params })
  },

  get(id: number) {
    return apiClient.get<Event>(`/events/${id}/`)
  },

  create(data: Omit<Event, 'id' | 'member_name' | 'event_type'>) {
    return apiClient.post<Event>('/events/', data)
  },

  update(id: number, data: Partial<Omit<Event, 'id' | 'member_name' | 'event_type'>>) {
    return apiClient.patch<Event>(`/events/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/events/${id}/`)
  }
}

export const eventTypesApi = {
  list() {
    return apiClient.get<EventType[]>('/event-types/')
  },

  get(id: number) {
    return apiClient.get<EventType>(`/event-types/${id}/`)
  },

  create(data: Omit<EventType, 'id'>) {
    return apiClient.post<EventType>('/event-types/', data)
  },

  update(id: number, data: Partial<Omit<EventType, 'id'>>) {
    return apiClient.patch<EventType>(`/event-types/${id}/`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/event-types/${id}/`)
  }
}
