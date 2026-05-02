import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { useGroupsStore } from '../groups'
import { groupsApi } from '@/api/members'

vi.mock('@/api/members')

function createMockAxiosResponse<T>(data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: { headers: {} } as InternalAxiosRequestConfig,
  }
}

describe('Groups Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('createGroup', () => {
    it('sends active department when selected', async () => {
      localStorage.setItem('activeDepartmentId', '7')
      const createdGroup = { id: 1, name: 'Alpha', department: 7 }
      vi.mocked(groupsApi.create).mockResolvedValue(createMockAxiosResponse(createdGroup))

      const store = useGroupsStore()
      await store.createGroup('Alpha')

      expect(groupsApi.create).toHaveBeenCalledWith({ name: 'Alpha', department: 7 })
      expect(store.groups).toEqual([createdGroup])
    })

    it('omits department when no active department is selected', async () => {
      const createdGroup = { id: 2, name: 'Beta', department: null }
      vi.mocked(groupsApi.create).mockResolvedValue(createMockAxiosResponse(createdGroup))

      const store = useGroupsStore()
      await store.createGroup('Beta')

      expect(groupsApi.create).toHaveBeenCalledWith({ name: 'Beta' })
      expect(store.groups).toEqual([createdGroup])
    })
  })
})
