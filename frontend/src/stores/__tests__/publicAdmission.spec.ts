import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePublicAdmissionStore } from '../publicAdmission'
import { publicAdmissionApi } from '@/api/admissions'

vi.mock('@/api/admissions', () => ({ publicAdmissionApi: { form: vi.fn(), submit: vi.fn(), verify: vi.fn() } }))

const form = {
  department: 'Mitte', title: 'Aufnahmeantrag', intro: '', signature_mode: 'both', decision_body: 'Jugendausschuss',
  version: 1, schema: { pages: [] }, prefill: { vorname: 'Mia' }, expires_at: '2026-12-31T00:00:00Z'
}

describe('public admission store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('opens a form and starts with the prefill', async () => {
    vi.mocked(publicAdmissionApi.form).mockResolvedValue({ data: form } as never)
    const store = usePublicAdmissionStore()
    await store.open('7KQ4-M2XR-9PDA')
    expect(publicAdmissionApi.form).toHaveBeenCalledWith('7KQ4-M2XR-9PDA')
    expect(store.answers).toEqual({ vorname: 'Mia' })
  })

  it('shows a plain message for unusable codes', async () => {
    vi.mocked(publicAdmissionApi.form).mockRejectedValue({ response: { status: 404, data: { detail: 'Der Code ist ungültig' } } })
    const store = usePublicAdmissionStore()
    await store.open('AAAA-BBBB-CCCC')
    expect(store.form).toBeNull()
    expect(store.error).toBeTruthy()
  })

  it('maps server errors to the fields', async () => {
    vi.mocked(publicAdmissionApi.form).mockResolvedValue({ data: form } as never)
    vi.mocked(publicAdmissionApi.submit).mockRejectedValue({ response: { status: 400, data: { answers: { vorname: 'Bitte ausfüllen.' } } } })
    const store = usePublicAdmissionStore()
    await store.open('7KQ4-M2XR-9PDA')
    await expect(store.submit()).rejects.toBeTruthy()
    expect(store.fieldErrors).toEqual({ vorname: 'Bitte ausfüllen.' })
    expect(store.error).toBe('Bitte die markierten Angaben prüfen.')
  })

  it('sends PDFs as multipart files and the rest as JSON payload', async () => {
    vi.mocked(publicAdmissionApi.form).mockResolvedValue({ data: form } as never)
    vi.mocked(publicAdmissionApi.submit).mockResolvedValue({ data: { applicant_name: 'Mia', submitted_at: '', seal: {} } } as never)
    const store = usePublicAdmissionStore()
    await store.open('7KQ4-M2XR-9PDA')
    const pdf = new File(['%PDF-1.4'], 'attest.pdf', { type: 'application/pdf' })
    store.setAnswers({ vorname: 'Mia', attest: pdf })
    await store.submit()
    const body = vi.mocked(publicAdmissionApi.submit).mock.calls[0]![1] as FormData
    expect(body).toBeInstanceOf(FormData)
    expect(JSON.parse(body.get('payload') as string)).toEqual({ answers: { vorname: 'Mia' } })
    expect((body.get('file:attest') as File).name).toBe('attest.pdf')
  })

  it('stays JSON without attachments', async () => {
    vi.mocked(publicAdmissionApi.form).mockResolvedValue({ data: form } as never)
    vi.mocked(publicAdmissionApi.submit).mockResolvedValue({ data: { applicant_name: 'Mia', submitted_at: '', seal: {} } } as never)
    const store = usePublicAdmissionStore()
    await store.open('7KQ4-M2XR-9PDA')
    await store.submit()
    expect(vi.mocked(publicAdmissionApi.submit).mock.calls[0]![1]).toEqual({ answers: { vorname: 'Mia' } })
  })
})
