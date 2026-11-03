import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAnnualReportStore } from '../annualReport'
import { annualReportApi } from '@/api/membership'

vi.mock('@/api/membership', () => ({
  annualReportApi: {
    preview: vi.fn(), saveManual: vi.fn(), finalize: vi.fn(), exportXlsx: vi.fn(), profiles: vi.fn(), createProfile: vi.fn(), updateProfile: vi.fn()
  }
}))

const response = (state: 'draft' | 'final') => ({ data: { state, data: { year: 2026, ok: true, manual: {} } } })

describe('annual report store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(annualReportApi.preview).mockResolvedValue(response('draft') as never)
    vi.mocked(annualReportApi.profiles).mockResolvedValue({ data: { count: 0, results: [] } } as never)
  })

  it('loads the report and the organisation profile for a department and year', async () => {
    const store = useAnnualReportStore()
    await store.load(3, 2026)
    expect(annualReportApi.preview).toHaveBeenCalledWith(3, 2026)
    expect(store.report?.state).toBe('draft')
    expect(store.profile).toBeNull()
  })

  it('creates the profile on first save and updates it afterwards', async () => {
    const profile = { id: 9, department: 3, djf_org_id: 'DE08215015001100001JF', org_kind: 'JF', founded_on: null, include_status_categories: ['active'] }
    vi.mocked(annualReportApi.createProfile).mockResolvedValue({ data: profile } as never)
    vi.mocked(annualReportApi.updateProfile).mockResolvedValue({ data: { ...profile, org_kind: 'KF' } } as never)
    const store = useAnnualReportStore()
    await store.saveProfile(3, { djf_org_id: 'DE08215015001100001JF' })
    expect(annualReportApi.createProfile).toHaveBeenCalledWith(expect.objectContaining({ department: 3, djf_org_id: 'DE08215015001100001JF' }))
    await store.saveProfile(3, { org_kind: 'KF' })
    expect(annualReportApi.updateProfile).toHaveBeenCalledWith(9, { org_kind: 'KF' })
  })

  it('keeps the error of a refused finalization', async () => {
    vi.mocked(annualReportApi.finalize).mockRejectedValue({ response: { status: 400, data: { detail: 'Festschreiben ist erst nach dem Stichtag möglich.' } } })
    const store = useAnnualReportStore()
    await expect(store.finalize(3, 2026)).rejects.toBeTruthy()
    expect(store.error).toBeTruthy()
  })
})
