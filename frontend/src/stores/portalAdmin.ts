import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  portalAdminApi,
  type AccessDetail, type AccessKind, type AccessRecord, type AccessState, type BulkResult,
  type EndingEntry, type PortalInvitation, type Subject,
} from '@/api/portalAdmin'
import { getApiErrorMessage } from '@/utils/apiError'

export interface ActionResult { ok: boolean, code?: string, message?: string }

function failure(err: unknown, fallback: string): ActionResult {
  const data = (err as { response?: { data?: { code?: string } } }).response?.data
  return { ok: false, code: data?.code, message: getApiErrorMessage(err, fallback) }
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

  const invite = (parent: number) => run(() => portalAdminApi.invite(parent), 'Einladung konnte nicht gesendet werden.', refreshAll())
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

  return {
    kind, stateFilter, search, pageSize, offset, records, count, loading, error, selected, selectedCount, inviteableSelected,
    bulkResults, busy, invitations, invitationsLoading, invitationsError, ending, endingLoading, endingError,
    detail, detailLoading, detailError,
    loadRecords, setFilter, toggleSelected, invite, resend, revoke, suspend, resume, endAccess, extend, bulkInvite,
    loadInvitations, loadEnding, loadDetail,
  }
})
