import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  portalAdminApi,
  type AccessDetail, type AccessKind, type AccessRecord, type AccessState, type BulkResult,
  type Audience, type Ceiling, type EndingEntry, type MemberPortalMode, type PerAudience, type PolicyOverview,
  type PolicyUpdate, type PortalInvitation, type Subject, type Visibility,
} from '@/api/portalAdmin'
import { getApiErrorMessage } from '@/utils/apiError'

export interface ActionResult { ok: boolean, code?: string, message?: string }

function failure(err: unknown, fallback: string): ActionResult {
  const data = (err as { response?: { data?: { code?: string } } }).response?.data
  return { ok: false, code: data?.code, message: getApiErrorMessage(err, fallback) }
}

export type PolicyScope = 'org' | number
export interface PolicyDraft {
  mode: '' | MemberPortalMode
  minAge: number | null
  visibility: Record<string, PerAudience<Visibility | ''>>
  ceiling: Record<string, PerAudience<Ceiling>>
}

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
export const STALE_MESSAGE = 'Die Freigaben wurden zwischenzeitlich von jemand anderem geändert. Die aktuelle Fassung wurde geladen; bitte Änderungen erneut vornehmen.'

/** The values stored on the server for a scope, in the shape the editor works with. */
export function policyBaseline(overview: PolicyOverview, scope: PolicyScope): PolicyDraft | null {
  if (scope === 'org') {
    const org = overview.organization
    return { mode: org.member_portal_mode, minAge: org.member_portal_min_age, visibility: clone(org.effective), ceiling: clone(org.ceiling) }
  }
  const dept = overview.departments.find(d => d.id === scope)
  if (!dept) return null
  return { mode: dept.member_portal_mode, minAge: dept.member_portal_min_age, visibility: clone(dept.overrides), ceiling: {} }
}

export const usePortalAdminStore = defineStore('portalAdmin', () => {
  const kind = ref<AccessKind>('parent')
  const stateFilter = ref<AccessState | ''>('')
  const search = ref('')
  const pageSize = ref(20)
  const offset = ref(0)
  const records = ref<AccessRecord[]>([])
  const count = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selected = ref<number[]>([])
  const bulkResults = ref<BulkResult[] | null>(null)
  const busy = ref(false)

  const invitations = ref<PortalInvitation[]>([])
  const invitationsLoading = ref(false)
  const invitationsError = ref<string | null>(null)

  const ending = ref<EndingEntry[]>([])
  const endingLoading = ref(false)
  const endingError = ref<string | null>(null)

  const detail = ref<AccessDetail | null>(null)
  const detailLoading = ref(false)
  const detailError = ref<string | null>(null)

  const overview = ref<PolicyOverview | null>(null)
  const policyLoading = ref(false)
  const policyError = ref<string | null>(null)
  const policyScope = ref<PolicyScope>('org')
  const policyDrafts = ref<Record<string, PolicyDraft>>({})
  const policySaving = ref(false)
  const policyErrors = ref<Record<string, string>>({})
  const policyNotice = ref<{ severity: 'success' | 'warn' | 'error', text: string } | null>(null)

  // Only the newest request may write results (filters change quickly while typing).
  let recordsSeq = 0
  const selectedCount = computed(() => selected.value.length)
  const inviteableSelected = computed(() => kind.value === 'parent'
    ? selected.value.filter(id => { const r = records.value.find(x => x.id === id); return !r || ['none', 'expired'].includes(r.state) })
    : [])

  async function loadRecords() {
    const seq = ++recordsSeq
    loading.value = true
    error.value = null
    try {
      const { data } = await portalAdminApi.records({
        kind: kind.value, state: stateFilter.value || undefined, search: search.value.trim() || undefined,
        limit: pageSize.value, offset: offset.value,
      })
      if (seq !== recordsSeq) return
      records.value = data.results
      count.value = data.count
    } catch (err) {
      if (seq !== recordsSeq) return
      error.value = getApiErrorMessage(err, 'Die Zugänge konnten nicht geladen werden.')
    } finally {
      if (seq === recordsSeq) loading.value = false
    }
  }

  function setFilter(patch: { kind?: AccessKind, state?: AccessState | '', search?: string, offset?: number }) {
    if (patch.kind !== undefined) kind.value = patch.kind
    if (patch.state !== undefined) stateFilter.value = patch.state
    if (patch.search !== undefined) search.value = patch.search
    offset.value = patch.offset ?? 0
    if (patch.offset === undefined) selected.value = []
    return loadRecords()
  }

  function toggleSelected(id: number, on: boolean) {
    selected.value = on ? [...new Set([...selected.value, id])] : selected.value.filter(x => x !== id)
  }

  async function run(action: () => Promise<unknown>, fallback: string, reload: Array<() => Promise<unknown>> = []): Promise<ActionResult> {
    busy.value = true
    try {
      await action()
      await Promise.all(reload.map(fn => fn()))
      return { ok: true }
    } catch (err) {
      return failure(err, fallback)
    } finally {
      busy.value = false
    }
  }

  const refreshAll = () => [loadRecords, loadInvitations, loadEnding]

  const invite = (id: number, kind: AccessKind = 'parent') => run(() => portalAdminApi.invite(id, kind), 'Einladung konnte nicht gesendet werden.', refreshAll())
  const resend = (id: number) => run(() => portalAdminApi.resend(id), 'Einladung konnte nicht erneut gesendet werden.', refreshAll())
  const revoke = (id: number) => run(() => portalAdminApi.revoke(id), 'Einladung konnte nicht widerrufen werden.', refreshAll())
  const suspend = (subject: Subject) => run(() => portalAdminApi.suspend(subject), 'Zugang konnte nicht gesperrt werden.', refreshAll())
  const resume = (subject: Subject) => run(() => portalAdminApi.resume(subject), 'Zugang konnte nicht entsperrt werden.', refreshAll())
  const endAccess = (subject: Subject) => run(() => portalAdminApi.end(subject), 'Zugang konnte nicht beendet werden.', refreshAll())
  const extend = (data: { parent: number, member: number, until: string, reason: string }) =>
    run(() => portalAdminApi.extend(data), 'Verlängerung konnte nicht gespeichert werden.', refreshAll())

  async function bulkInvite(ids = inviteableSelected.value): Promise<ActionResult> {
    busy.value = true
    try {
      const { data } = await portalAdminApi.bulkInvite(ids)
      bulkResults.value = data.results
      selected.value = []
      await loadRecords()
      return { ok: true }
    } catch (err) {
      return failure(err, 'Die Einladungen konnten nicht versendet werden.')
    } finally {
      busy.value = false
    }
  }

  async function loadInvitations() {
    invitationsLoading.value = true
    invitationsError.value = null
    try {
      const { data } = await portalAdminApi.invitations({ limit: 100 })
      const rank = (i: PortalInvitation) => (i.state === 'open' ? 0 : i.state === 'expired' ? 1 : 2)
      invitations.value = [...data.results].sort((a, b) => rank(a) - rank(b))
    } catch (err) {
      invitationsError.value = getApiErrorMessage(err, 'Die Einladungen konnten nicht geladen werden.')
    } finally {
      invitationsLoading.value = false
    }
  }

  async function loadEnding() {
    endingLoading.value = true
    endingError.value = null
    try {
      ending.value = (await portalAdminApi.ending()).data
    } catch (err) {
      endingError.value = getApiErrorMessage(err, 'Die Liste konnte nicht geladen werden.')
    } finally {
      endingLoading.value = false
    }
  }

  async function loadDetail(subject: Subject) {
    detailLoading.value = true
    detailError.value = null
    detail.value = null
    try {
      detail.value = (await portalAdminApi.detail(subject)).data
    } catch (err) {
      detailError.value = getApiErrorMessage(err, 'Details konnten nicht geladen werden.')
    } finally {
      detailLoading.value = false
    }
  }

  const scopeKey = (scope: PolicyScope) => String(scope)
  const policyBase = computed(() => (overview.value ? policyBaseline(overview.value, policyScope.value) : null))
  /** Draft being edited for the current scope (the stored values until something is changed). */
  const policyDraft = computed<PolicyDraft | null>(() => policyDrafts.value[scopeKey(policyScope.value)] ?? policyBase.value)
  const policyDirty = computed(() => !!policyBase.value && !!policyDraft.value
    && JSON.stringify(policyBase.value) !== JSON.stringify(policyDraft.value))

  function ensureDraft(): PolicyDraft | null {
    const key = scopeKey(policyScope.value)
    if (!policyDrafts.value[key] && policyBase.value) policyDrafts.value[key] = clone(policyBase.value)
    return policyDrafts.value[key] ?? null
  }
  function editVisibility(category: string, audience: Audience, value: Visibility | '') {
    const draft = ensureDraft()
    if (!draft) return
    const cell = { ...draft.visibility[category] }
    if (value === '') delete cell[audience]
    else cell[audience] = value
    draft.visibility[category] = cell
    delete policyErrors.value[`${category}.${audience}`]
  }
  function editCeiling(category: string, audience: Audience, value: Ceiling) {
    const draft = ensureDraft()
    if (!draft) return
    draft.ceiling[category] = { ...draft.ceiling[category], [audience]: value }
    delete policyErrors.value[`${category}.${audience}`]
  }
  function editMode(mode: '' | MemberPortalMode) {
    const draft = ensureDraft()
    if (!draft) return
    draft.mode = mode
    if (mode === 'min_age' && draft.minAge === null) draft.minAge = policyBase.value?.minAge ?? null
    delete policyErrors.value.member_portal_mode
  }
  function editMinAge(age: number | null) {
    const draft = ensureDraft()
    if (!draft) return
    draft.minAge = age
    delete policyErrors.value.member_portal_min_age
  }
  function discardPolicy() {
    delete policyDrafts.value[scopeKey(policyScope.value)]
    policyErrors.value = {}
    policyNotice.value = null
  }
  function setPolicyScope(scope: PolicyScope) {
    policyScope.value = scope
    policyErrors.value = {}
    policyNotice.value = null
  }

  async function loadPolicies(keepDrafts = true) {
    policyLoading.value = true
    policyError.value = null
    try {
      overview.value = (await portalAdminApi.policies()).data
      if (!keepDrafts) policyDrafts.value = {}
      if (policyScope.value !== 'org' && !overview.value.departments.some(d => d.id === policyScope.value)) policyScope.value = 'org'
    } catch (err) {
      policyError.value = getApiErrorMessage(err, 'Die Freigaben konnten nicht geladen werden.')
    } finally {
      policyLoading.value = false
    }
  }

  /** Only what differs from the stored values is sent; the server merges it. */
  function policyPayload(version: number): PolicyUpdate | null {
    const base = policyBase.value
    const draft = policyDraft.value
    if (!base || !draft) return null
    const payload: PolicyUpdate = { version }
    // A cell that vanished from the draft was reset to "like the organisation" (sent as '').
    const diff = <T>(a: Record<string, PerAudience<T>>, b: Record<string, PerAudience<T>>, cleared?: T) => {
      const out: Record<string, PerAudience<T>> = {}
      for (const cat of Object.keys({ ...a, ...b })) {
        for (const aud of ['parents', 'members'] as Audience[]) {
          const before = a[cat]?.[aud]
          const after = b[cat]?.[aud] ?? (before !== undefined ? cleared : undefined)
          if (after !== undefined && before !== after) out[cat] = { ...out[cat], [aud]: after }
        }
      }
      return out
    }
    const visibility = diff<Visibility | ''>(base.visibility, draft.visibility, '')
    if (Object.keys(visibility).length) payload.visibility = visibility
    const ceiling = diff<Ceiling>(base.ceiling, draft.ceiling)
    if (Object.keys(ceiling).length) payload.ceiling = ceiling
    if (draft.mode !== base.mode) payload.member_portal_mode = draft.mode
    if (draft.mode === 'min_age' && (draft.minAge !== base.minAge || draft.mode !== base.mode)) payload.member_portal_min_age = draft.minAge
    return payload
  }

  async function savePolicy(): Promise<ActionResult> {
    const scope = policyScope.value
    const version = scope === 'org' ? overview.value?.organization.version : overview.value?.departments.find(d => d.id === scope)?.version
    const payload = version === undefined ? null : policyPayload(version)
    if (!payload) return { ok: false }
    policySaving.value = true
    policyErrors.value = {}
    policyNotice.value = null
    try {
      overview.value = (await portalAdminApi.savePolicy(scope, payload)).data
      delete policyDrafts.value[scopeKey(scope)]
      policyNotice.value = { severity: 'success', text: 'Die Freigaben wurden gespeichert.' }
      return { ok: true }
    } catch (err) {
      const response = (err as { response?: { status?: number, data?: Record<string, unknown> } }).response
      if (response?.status === 409 && response.data?.code === 'stale') {
        delete policyDrafts.value[scopeKey(scope)]
        policyNotice.value = { severity: 'warn', text: STALE_MESSAGE }
        await loadPolicies()
        return { ok: false, code: 'stale', message: STALE_MESSAGE }
      }
      if (response?.status === 400 && response.data) {
        const fields: Record<string, string> = {}
        for (const [key, value] of Object.entries(response.data)) {
          const text = Array.isArray(value) ? String(value[0]) : typeof value === 'string' ? value : ''
          if (text) fields[key] = text
        }
        policyErrors.value = fields
        policyNotice.value = { severity: 'error', text: 'Bitte prüfe die markierten Eingaben.' }
        return { ok: false, code: 'invalid', message: 'Bitte prüfe die markierten Eingaben.' }
      }
      const result = failure(err, 'Die Freigaben konnten nicht gespeichert werden.')
      policyNotice.value = { severity: 'error', text: result.message ?? '' }
      return result
    } finally {
      policySaving.value = false
    }
  }

  return {
    overview, policyLoading, policyError, policyScope, policyDraft, policyDirty, policySaving, policyErrors, policyNotice,
    loadPolicies, setPolicyScope, editVisibility, editCeiling, editMode, editMinAge, discardPolicy, savePolicy,
    kind, stateFilter, search, pageSize, offset, records, count, loading, error, selected, selectedCount, inviteableSelected,
    bulkResults, busy, invitations, invitationsLoading, invitationsError, ending, endingLoading, endingError,
    detail, detailLoading, detailError,
    loadRecords, setFilter, toggleSelected, invite, resend, revoke, suspend, resume, endAccess, extend, bulkInvite,
    loadInvitations, loadEnding, loadDetail,
  }
})
