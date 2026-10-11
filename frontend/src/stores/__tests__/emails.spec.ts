import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useEmailsStore } from '../emails'

const { checkRecipients } = vi.hoisted(() => ({ checkRecipients: vi.fn() }))
vi.mock('@/api/emails', () => ({ emailsApi: { checkRecipients } }))

const result = (count: number) => ({
  data: { count, member_count: count, personalized: false, merged_duplicates: 0, recipients: [], excluded: [] },
})

describe('emails store recipient check', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    checkRecipients.mockReset()
  })

  it('keeps the newest selection when an older answer arrives late', async () => {
    let resolveOld: (value: unknown) => void = () => {}
    checkRecipients
      .mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve }))
      .mockResolvedValueOnce(result(5))
    const store = useEmailsStore()

    const old = store.checkRecipients({ recipient_type: 'all' })
    await store.checkRecipients({ recipient_type: 'group', recipient_group: 2 })
    resolveOld(result(99))
    await old

    expect(store.recipientCheck?.count).toBe(5)
    expect(store.checkingRecipients).toBe(false)
  })

  it('reports a failed check without keeping stale numbers', async () => {
    checkRecipients.mockResolvedValueOnce(result(3)).mockRejectedValueOnce({ response: { data: { error: 'Gruppe nicht gefunden oder kein Zugriff' } } })
    const store = useEmailsStore()

    await store.checkRecipients({ recipient_type: 'all' })
    await expect(store.checkRecipients({ recipient_type: 'group', recipient_group: 9 })).rejects.toBeTruthy()

    expect(store.recipientCheck).toBeNull()
    expect(store.recipientCheckError).toBe('Gruppe nicht gefunden oder kein Zugriff')
  })
})
