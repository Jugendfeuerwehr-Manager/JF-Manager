import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useServicebookStore } from '../servicebook'
import { useDepartmentsStore } from '../departments'
import servicebookApi from '@/api/servicebook'

vi.mock('@/api/servicebook', () => ({
  default: { services: { create: vi.fn() } },
}))
const create = vi.mocked(servicebookApi.services.create)
const form = { start: '2026-11-01T18:00:00Z', end: '2026-11-01T20:00:00Z', topic: 'Übung' }

describe('servicebook store – createService', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
    create.mockResolvedValue({ data: { id: 15, ...form } } as never)
  })

  it('sends the active department with the new service', async () => {
    useDepartmentsStore().setActiveDepartment(1)
    await useServicebookStore().createService(form)
    expect(create).toHaveBeenCalledWith({ ...form, department: 1 })
  })

  it('keeps an explicitly chosen department', async () => {
    useDepartmentsStore().setActiveDepartment(1)
    await useServicebookStore().createService({ ...form, department: 3 })
    expect(create).toHaveBeenCalledWith({ ...form, department: 3 })
  })
})
