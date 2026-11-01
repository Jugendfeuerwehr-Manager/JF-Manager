import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ServiceForm from '../ServiceForm.vue'
import { useUsersStore } from '@/stores/users'
import { useDepartmentsStore } from '@/stores/departments'
import { useAuthStore } from '@/stores/auth'

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

describe('service department', () => {
  const departments = [{ id: 1, name: 'Süd-Ost' }, { id: 2, name: 'Mitte' }] as never
  const service = { start: '2026-11-01T18:00:00Z', end: '2026-11-01T20:00:00Z', operations_manager: [] }

  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.spyOn(useUsersStore(), 'fetchUsers').mockResolvedValue([] as never)
  })

  const departmentSelect = (wrapper: ReturnType<typeof shallowMount>) => wrapper.findComponent({ name: 'Select' })
  const optionsOf = (wrapper: ReturnType<typeof shallowMount>) =>
    (wrapper.vm as unknown as { departmentOptions: { id: number | string; name: string }[] }).departmentOptions

  it('is not asked when a department is active', async () => {
    const store = useDepartmentsStore()
    store.departments = departments
    store.setActiveDepartment(1)
    const wrapper = shallowMount(ServiceForm)
    await flushPromises()
    expect(departmentSelect(wrapper).exists()).toBe(false)
  })

  it('is required in the all-departments view and sent with the service', async () => {
    useDepartmentsStore().departments = departments
    const wrapper = shallowMount(ServiceForm, { props: { initialData: null } })
    await flushPromises()
    ;(wrapper.vm as unknown as { formData: { start: Date; end: Date } }).formData.start = new Date(service.start)
    ;(wrapper.vm as unknown as { formData: { start: Date; end: Date } }).formData.end = new Date(service.end)
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.text()).toContain('Bitte eine Abteilung wählen')

    departmentSelect(wrapper).vm.$emit('update:modelValue', 2)
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({ department: 2 })
  })

  it('lets organisation-wide accounts create a service for all departments', async () => {
    useDepartmentsStore().departments = departments
    useAuthStore().user = { has_org_wide_access: true } as never
    const wrapper = shallowMount(ServiceForm, { props: { initialData: null } })
    await flushPromises()
    expect(optionsOf(wrapper)[0]).toEqual({ id: 'organisation', name: 'Alle Abteilungen (gemeinsamer Dienst)' })
    ;(wrapper.vm as unknown as { formData: { start: Date; end: Date } }).formData.start = new Date(service.start)
    ;(wrapper.vm as unknown as { formData: { start: Date; end: Date } }).formData.end = new Date(service.end)
    departmentSelect(wrapper).vm.$emit('update:modelValue', 'organisation')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({ department: null })
  })

  it('does not offer the organisation-wide choice to department roles', async () => {
    useDepartmentsStore().departments = departments
    const wrapper = shallowMount(ServiceForm, { props: { initialData: null } })
    await flushPromises()
    expect(optionsOf(wrapper).map((o) => o.id)).toEqual([1, 2])
  })

  it('lets a service without department be assigned to one', async () => {
    const store = useDepartmentsStore()
    store.departments = departments
    store.setActiveDepartment(1)
    const wrapper = shallowMount(ServiceForm, { props: { initialData: { ...service, department: null } as never } })
    await flushPromises()
    expect(departmentSelect(wrapper).exists()).toBe(true)
  })
})
