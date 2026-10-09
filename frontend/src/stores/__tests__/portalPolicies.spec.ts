import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePortalAdminStore } from '../portalAdmin'
import { portalAdminApi, type PolicyOverview } from '@/api/portalAdmin'

vi.mock('@/api/portalAdmin', () => ({ portalAdminApi: { policies: vi.fn(), savePolicy: vi.fn() } }))
const api = vi.mocked(portalAdminApi)

function overview(version = 1): PolicyOverview {
  return {
    categories: [
      { key: 'swimming', label: 'Schwimmfähigkeit', hint: 'h', fixed: false, audiences: ['parents', 'members'] },
    ],
    never_visible: 'Notizen sind nie sichtbar.',
    organization: {
      editable: true, version, member_portal_mode: 'off', member_portal_min_age: null,
      effective: { swimming: { parents: 'visible', members: 'hidden' } },
      ceiling: { swimming: { parents: 'allowed', members: 'allowed' } },
    },
    departments: [{
      id: 5, name: 'Mitte', editable: true, version: 3, member_portal_mode: '', member_portal_min_age: null,
      overrides: { swimming: { parents: 'hidden' } },
      effective: { swimming: { parents: 'hidden', members: 'hidden' } },
      locked: { swimming: { parents: false, members: false } },
      member_portal: { mode: 'off', min_age: null, eligible: 0, missing_birthday: 0 },
    }],
  }
}
const apiError = (status: number, data: Record<string, unknown>) => Object.assign(new Error('x'), { response: { status, data } })

describe('portal policy store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.policies.mockResolvedValue({ data: overview() } as never)
  })

  it('loads the overview and starts clean', async () => {
    const store = usePortalAdminStore()
    await store.loadPolicies()
    expect(store.overview?.categories).toHaveLength(1)
    expect(store.policyDirty).toBe(false)
    expect(store.policyDraft?.visibility.swimming).toEqual({ parents: 'visible', members: 'hidden' })
  })

  it('reports a load error', async () => {
    api.policies.mockRejectedValue(apiError(403, { detail: 'Keine Berechtigung' }))
    const store = usePortalAdminStore()
    await store.loadPolicies()
    expect(store.policyError).toBe('Keine Berechtigung')
  })

  it('tracks dirty state, sends only changed cells with the version and resets after saving', async () => {
    const store = usePortalAdminStore()
    await store.loadPolicies()
    store.editVisibility('swimming', 'members', 'visible')
    store.editCeiling('swimming', 'parents', 'locked')
    expect(store.policyDirty).toBe(true)
    api.savePolicy.mockResolvedValue({ data: overview(2) } as never)
    expect((await store.savePolicy()).ok).toBe(true)
    expect(api.savePolicy).toHaveBeenCalledWith('org', {
      version: 1, visibility: { swimming: { members: 'visible' } }, ceiling: { swimming: { parents: 'locked' } },
    })
    expect(store.policyDirty).toBe(false)
    expect(store.overview?.organization.version).toBe(2)
    expect(store.policyNotice?.severity).toBe('success')
  })

  it('discards changes', async () => {
    const store = usePortalAdminStore()
    await store.loadPolicies()
    store.editVisibility('swimming', 'members', 'visible')
    store.discardPolicy()
    expect(store.policyDirty).toBe(false)
  })

  it('sends "" when a department resets a cell to the organisation value and the member mode', async () => {
    const store = usePortalAdminStore()
    await store.loadPolicies()
    store.setPolicyScope(5)
    store.editVisibility('swimming', 'parents', '')
    store.editMode('min_age')
    store.editMinAge(10)
    api.savePolicy.mockResolvedValue({ data: overview() } as never)
    await store.savePolicy()
    expect(api.savePolicy).toHaveBeenCalledWith(5, {
      version: 3, visibility: { swimming: { parents: '' } }, member_portal_mode: 'min_age', member_portal_min_age: 10,
    })
  })

  it('reloads and tells the user on a stale version (409)', async () => {
    const store = usePortalAdminStore()
    await store.loadPolicies()
    store.editVisibility('swimming', 'members', 'visible')
    api.savePolicy.mockRejectedValue(apiError(409, { code: 'stale' }))
    api.policies.mockResolvedValue({ data: overview(7) } as never)
    const result = await store.savePolicy()
    expect(result.code).toBe('stale')
    expect(api.policies).toHaveBeenCalledTimes(2)
    expect(store.overview?.organization.version).toBe(7)
    expect(store.policyDirty).toBe(false)
    expect(store.policyNotice?.text).toContain('von jemand anderem geändert')
  })

  it('keeps the draft and exposes cell errors on 400', async () => {
    const store = usePortalAdminStore()
    await store.loadPolicies()
    store.editMode('min_age')
    store.editVisibility('swimming', 'parents', 'hidden')
    api.savePolicy.mockRejectedValue(apiError(400, { 'swimming.parents': ['Gesperrt.'], member_portal_min_age: ['Pflichtfeld.'] }))
    const result = await store.savePolicy()
    expect(result.ok).toBe(false)
    expect(store.policyErrors).toEqual({ 'swimming.parents': 'Gesperrt.', member_portal_min_age: 'Pflichtfeld.' })
    expect(store.policyDirty).toBe(true)
    store.editVisibility('swimming', 'parents', 'visible')
    expect(store.policyErrors['swimming.parents']).toBeUndefined()
  })
})
