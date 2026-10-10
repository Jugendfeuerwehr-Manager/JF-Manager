import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { api } = vi.hoisted(() => ({ api: { preview: vi.fn() } }))
vi.mock('@/api/externalSync', () => ({ externalSyncApi: api }))

import { useExternalSyncStore } from '../externalSync'

describe('external sync change preview (UX-08.1)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    api.preview.mockReset()
  })

  it('keeps the counts until discarded and reports failures', async () => {
    const counts = { imported_members: 1, imported_groups: 0, updated_members: 2, updated_groups: 0, flagged_for_review: 3, deleted_objects: 0 }
    api.preview.mockResolvedValueOnce({ data: { job: 4, counts } })
    const store = useExternalSyncStore()
    await store.previewRun(4)
    expect(store.changePreview?.counts.flagged_for_review).toBe(3)
    expect(store.actionJobId).toBeNull()
    store.clearChangePreview()
    expect(store.changePreview).toBeNull()

    api.preview.mockRejectedValueOnce({ response: { status: 502, data: { detail: 'Spond nicht erreichbar' } } })
    await expect(store.previewRun(4)).rejects.toBeTruthy()
    expect(store.error).toBe('Spond nicht erreichbar')
  })
})
