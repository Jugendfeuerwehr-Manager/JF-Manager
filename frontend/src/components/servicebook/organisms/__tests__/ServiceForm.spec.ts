import { describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ServiceForm from '../ServiceForm.vue'
import { useUsersStore } from '@/stores/users'

vi.mock('@/api/settings', () => ({ settingsApi: { getService: vi.fn().mockResolvedValue({ data: {}, headers: {} }) } }))

describe('service lead picker', () => {
  it('offers active accounts and keeps an already assigned, now inactive lead by name', async () => {
    setActivePinia(createPinia())
    const users = useUsersStore()
    const fetchUsers = vi.spyOn(users, 'fetchUsers').mockImplementation(async () => {
      users.users = [{ id: 1, username: 'aktiv', full_name: 'Alex Aktiv' }] as never
      return users.users
    })
    const wrapper = shallowMount(ServiceForm, {
      props: { initialData: { operations_manager: [{ id: 9, username: 'alt', full_name: 'Robin Alt', email: '' }] } as never },
    })
    await flushPromises()
    expect(fetchUsers).toHaveBeenCalledWith({ limit: 1000, is_active: true })
    expect(wrapper.findComponent({ name: 'UserChipSelector' }).props('options')).toEqual([
      { label: 'Alex Aktiv', value: 1 },
      { label: 'Robin Alt (inaktiv)', value: 9 },
    ])
  })
})
