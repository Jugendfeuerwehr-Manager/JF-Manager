import { defineComponent, h, reactive } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useRoleMemberOptions } from '../useRoleMemberOptions'

const mock = vi.hoisted(() => ({ get: vi.fn(), department: { activeDepartmentId: 1 as number | null } }))
vi.mock('@/api', () => ({ default: { get: mock.get } }))
vi.mock('@/stores/departments', () => ({ useDepartmentsStore: () => reactive(mock.department) }))

function setup() {
  let options!: ReturnType<typeof useRoleMemberOptions>
  const wrapper = mount(defineComponent({ setup() { options = useRoleMemberOptions('inventory'); return () => h('div') } }))
  return { wrapper, options }
}
beforeEach(() => { mock.get.mockReset(); mock.department.activeDepartmentId = 1 })

describe('minimal operational member selection', () => {
  it('loads every page with the purpose and selected department', async () => {
    mock.get.mockResolvedValueOnce({ data: { results: [{ id: 1, full_name: 'Test A', department_ids: [1] }], next: 'next' } })
      .mockResolvedValueOnce({ data: { results: [{ id: 2, full_name: 'Test B', department_ids: [1] }], next: null } })
    const { wrapper, options } = setup()
    await flushPromises()
    expect(options.memberOptions.value).toEqual([{ value: 1, label: 'Test A' }, { value: 2, label: 'Test B' }])
    expect(mock.get).toHaveBeenLastCalledWith('/role-member-options/', { params: { purpose: 'inventory', limit: 100, offset: 1, department: 1 } })
    wrapper.unmount()
  })
  it('discards delayed results after the department changes', async () => {
    let resolve!: (value: unknown) => void
    mock.get.mockImplementationOnce(() => new Promise(r => { resolve = r }))
      .mockResolvedValueOnce({ data: { results: [{ id: 2, full_name: 'Current', department_ids: [2] }], next: null } })
    const { wrapper, options } = setup()
    reactive(mock.department).activeDepartmentId = 2
    await flushPromises()
    resolve({ data: { results: [{ id: 1, full_name: 'Old', department_ids: [1] }], next: null } })
    await flushPromises()
    expect(options.members.value.map(person => person.id)).toEqual([2])
    wrapper.unmount()
  })
  it('clears previous names when access fails', async () => {
    mock.get.mockResolvedValueOnce({ data: { results: [{ id: 1, full_name: 'Test', department_ids: [1] }], next: null } })
    const { wrapper, options } = setup()
    await flushPromises()
    mock.get.mockRejectedValueOnce(new Error('Denied'))
    await options.load()
    expect(options.members.value).toEqual([])
    expect(options.error.value).toBeTruthy()
    wrapper.unmount()
  })
})
