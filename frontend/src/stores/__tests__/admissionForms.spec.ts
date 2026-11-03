import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAdmissionFormsStore } from '../admissionForms'
import { admissionFormsApi, admissionTextBlocksApi } from '@/api/admissions'
import type { AdmissionForm, FormSchema } from '@/types/admissions'

vi.mock('@/api/admissions', () => ({
  admissionFormsApi: { get: vi.fn(), update: vi.fn(), references: vi.fn(), publish: vi.fn(), list: vi.fn(), create: vi.fn(), versions: vi.fn() },
  admissionTextBlocksApi: { list: vi.fn() }
}))

const empty: FormSchema = { pages: [] }
const withPage: FormSchema = { pages: [{ id: 'p', title: 'Seite', sections: [] }] }
const form = (draft: FormSchema): AdmissionForm => ({
  id: 3, department: 1, title: 'Antrag', intro: '', initial_status: null, signature_mode: 'both', decision_body: 'Jugendausschuss',
  is_active: true, draft_schema: draft, draft_issues: [], has_unpublished_changes: true, current_version: null, updated_at: ''
})

describe('admission forms store', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(admissionFormsApi.get).mockResolvedValue({ data: form(empty) } as never)
    vi.mocked(admissionFormsApi.references).mockResolvedValue({ data: { fields: { member: [], guardian: [], gender_options: [] }, legal_kinds: [], consent_kinds: [] } } as never)
    vi.mocked(admissionTextBlocksApi.list).mockResolvedValue({ data: { count: 0, results: [] } } as never)
  })

  it('keeps an undo and redo history of draft edits', async () => {
    const store = useAdmissionFormsStore()
    await store.openForm(3)
    store.edit(withPage)
    expect(store.dirty).toBe(true)
    store.undo()
    expect(store.draft).toEqual(empty)
    expect(store.canRedo).toBe(true)
    store.redo()
    expect(store.draft).toEqual(withPage)
    store.undo()
    store.edit({ pages: [] })
    expect(store.canRedo).toBe(false)
  })

  it('saves the draft once and clears the dirty flag', async () => {
    const store = useAdmissionFormsStore()
    await store.openForm(3)
    vi.mocked(admissionFormsApi.update).mockResolvedValue({ data: form(withPage) } as never)
    store.edit(withPage)
    await store.saveDraft()
    expect(admissionFormsApi.update).toHaveBeenCalledWith(3, { draft_schema: withPage })
    expect(store.dirty).toBe(false)
    await store.saveDraft()
    expect(admissionFormsApi.update).toHaveBeenCalledTimes(1)
  })

  it('reports a failed save and keeps the changes', async () => {
    const store = useAdmissionFormsStore()
    await store.openForm(3)
    vi.mocked(admissionFormsApi.update).mockRejectedValue(new Error('offline'))
    store.edit(withPage)
    await expect(store.saveDraft()).rejects.toThrow()
    expect(store.dirty).toBe(true)
    expect(store.error).toBeTruthy()
  })
})
