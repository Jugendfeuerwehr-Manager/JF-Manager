import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useMemberDuplicates } from '../useMemberDuplicates'

const list = vi.fn()
vi.mock('@/api/members', () => ({ membersApi: { list: (...args: unknown[]) => list(...args) } }))

const member = (id: number, name: string, lastname: string) => ({ id, name, lastname, full_name: `${name} ${lastname}` })

describe('member duplicate hint', () => {
  it('suggests only exact name matches on the same birthday within the visible members', async () => {
    list.mockResolvedValue({ data: { results: [member(1, 'Mia', 'Beispiel'), member(2, 'Miabella', 'Beispiel')] } })
    const first = ref(' mia '), last = ref('Beispiel'), birthday = ref<Date | null>(new Date(2012, 4, 3)), enabled = ref(true)
    const { duplicates, check } = useMemberDuplicates(first, last, birthday, enabled, 0)
    await check()
    expect(list).toHaveBeenCalledWith({ search: 'Beispiel', birthday: '2012-05-03', limit: 10 })
    expect(duplicates.value).toEqual([{ id: 1, name: 'Mia Beispiel' }])
  })

  it('stays silent while editing, with missing fields or when the lookup fails', async () => {
    list.mockReset()
    const birthday = ref<Date | null>(new Date(2012, 4, 3))
    const editing = useMemberDuplicates(ref('Mia'), ref('Beispiel'), birthday, ref(false), 0)
    await editing.check()
    const incomplete = useMemberDuplicates(ref('Mia'), ref(''), birthday, ref(true), 0)
    await incomplete.check()
    expect(list).not.toHaveBeenCalled()
    list.mockRejectedValueOnce(new Error('offline'))
    const failing = useMemberDuplicates(ref('Mia'), ref('Beispiel'), birthday, ref(true), 0)
    await failing.check()
    expect(failing.duplicates.value).toEqual([])
  })
})
