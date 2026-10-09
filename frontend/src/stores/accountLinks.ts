import { defineStore } from 'pinia'
import { ref } from 'vue'
import { accountLinksApi } from '@/api/accountLinks'
import type { AccountCandidate, AccountLink, AccountLinkRecordKind, AccountLinkResult } from '@/types/accountLinks'
import { classifyApiError, getApiErrorMessage, type ApiErrorKind } from '@/utils/apiError'

function failure(err: unknown, fallback: string): AccountLinkResult {
  const data = (err as { response?: { data?: { code?: string } } }).response?.data
  return { ok: false, code: data?.code ?? 'error', message: getApiErrorMessage(err, fallback) }
}

/** Account management: the link of one member or parent record (PORTAL-04.1). */
export const useAccountLinksStore = defineStore('accountLinks', () => {
  const record = ref<{ kind: AccountLinkRecordKind, id: number } | null>(null)
  const link = ref<AccountLink | null>(null)
  const loading = ref(false)
  const error = ref<ApiErrorKind | null>(null)
  const suggestions = ref<AccountCandidate[]>([])
  const searchResults = ref<AccountCandidate[]>([])
  const searching = ref(false)
  const busy = ref(false)
  let seq = 0

  async function load(kind: AccountLinkRecordKind, id: number) {
    const current = ++seq
    record.value = { kind, id }
    loading.value = true
    error.value = null
    try {
      const { data } = await accountLinksApi.forRecord(kind, id)
      if (current !== seq) return
      // A rejected link has no effect; it is shown until a new one replaces it.
      link.value = data.results[0] ?? null
    } catch (err) {
      if (current !== seq) return
      link.value = null
      error.value = classifyApiError(err)
    } finally {
      if (current === seq) loading.value = false
    }
  }

  async function loadSuggestions() {
    suggestions.value = []
    if (!record.value) return
    try {
      suggestions.value = (await accountLinksApi.suggestions(record.value.kind, record.value.id)).data.results
    } catch { /* suggestions are optional; search still works */ }
  }

  let searchSeq = 0
  async function search(text: string) {
    const current = ++searchSeq
    searching.value = true
    try {
      const { data } = await accountLinksApi.searchAccounts(text.trim())
      if (current === searchSeq) searchResults.value = data.results
    } catch {
      if (current === searchSeq) searchResults.value = []
    } finally {
      if (current === searchSeq) searching.value = false
    }
  }

  function clearSearch() {
    searchSeq++
    searchResults.value = []
    searching.value = false
  }

  async function linkAccount(userId: number, transfer = false): Promise<AccountLinkResult> {
    if (!record.value || busy.value) return { ok: false, code: 'busy' }
    busy.value = true
    try {
      const { data } = await accountLinksApi.link({ user: userId, [record.value.kind]: record.value.id, transfer })
      link.value = data
      return { ok: true }
    } catch (err) {
      return failure(err, 'Die Verknüpfung konnte nicht gespeichert werden.')
    } finally {
      busy.value = false
    }
  }

  async function unlink(): Promise<AccountLinkResult> {
    if (!record.value || !link.value || busy.value) return { ok: false, code: 'busy' }
    busy.value = true
    try {
      // Only this record is released; a second record of the same account stays linked.
      await accountLinksApi.unlink(link.value.id, record.value.kind)
      link.value = null
      return { ok: true }
    } catch (err) {
      return failure(err, 'Die Verknüpfung konnte nicht gelöst werden.')
    } finally {
      busy.value = false
    }
  }

  return { record, link, loading, error, suggestions, searchResults, searching, busy, load, loadSuggestions, search, clearSearch, linkAccount, unlink }
})
