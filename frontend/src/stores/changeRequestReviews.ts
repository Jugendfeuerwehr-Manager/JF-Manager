import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { changeRequestsApi } from '@/api/changeRequests'
import type { ChangeRequestErrorBody, DecidePayload, Review } from '@/types/changeRequests'
import { getApiErrorMessage } from '@/utils/apiError'

export type ReviewScope = 'open' | 'decided'

/** Staff side: review and decide change requests (PORTAL-03.3). */
export const useChangeRequestReviewsStore = defineStore('changeRequestReviews', () => {
  const scope = ref<ReviewScope>('open')
  const open = ref<Review[]>([])
  const decided = ref<Review[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const selectedId = ref<number | null>(null)
  const busy = ref(false)
  const decideError = ref<string | null>(null)
  const decideFields = ref<string[]>([])
  /** Shown after the view was refreshed because of a concurrent change. */
  const notice = ref<string | null>(null)
  let seq = 0

  const list = computed(() => (scope.value === 'open' ? open.value : decided.value))
  const selected = computed(() => list.value.find(r => r.id === selectedId.value) ?? null)

  async function load(which: ReviewScope = scope.value) {
    const mine = ++seq
    loading.value = true
    error.value = null
    try {
      const results = (await changeRequestsApi.reviews(which)).data.results
      if (mine !== seq) return
      if (which === 'open') open.value = results
      else decided.value = results
      if (which === scope.value && !results.some(r => r.id === selectedId.value)) selectedId.value = results[0]?.id ?? null
    } catch (err) {
      if (mine !== seq) return
      const status = (err as { response?: { status?: number } }).response?.status
      error.value = status === 403 ? 'Dir fehlt die Berechtigung, Änderungsanträge zu prüfen.' : getApiErrorMessage(err, 'Die Anträge konnten nicht geladen werden.')
    } finally {
      if (mine === seq) loading.value = false
    }
  }

  async function setScope(next: ReviewScope) {
    scope.value = next
    selectedId.value = null
    clearMessages()
    await load(next)
  }

  function select(id: number) {
    selectedId.value = id
    clearMessages()
  }

  function clearMessages() { decideError.value = null; decideFields.value = []; notice.value = null }

  async function decide(review: Review, payload: Omit<DecidePayload, 'version'>): Promise<boolean> {
    if (busy.value || review.own) return false
    busy.value = true
    clearMessages()
    try {
      const { data } = await changeRequestsApi.decide(review.id, { ...payload, version: review.version })
      open.value = open.value.filter(r => r.id !== data.id)
      decided.value = [data, ...decided.value.filter(r => r.id !== data.id)]
      selectedId.value = open.value[0]?.id ?? null
      notice.value = `Entscheidung für ${data.person_name} gespeichert.`
      return true
    } catch (err) {
      const response = (err as { response?: { status?: number, data?: ChangeRequestErrorBody } }).response
      const body = response?.data ?? {}
      decideFields.value = Object.keys(body.fields ?? {})
      switch (body.code) {
        case 'outdated':
          decideError.value = 'Der Antrag wurde inzwischen geändert. Die Ansicht wurde aktualisiert, bitte prüfe ihn erneut. Deine Entscheidung wurde nicht gespeichert.'
          await load('open')
          break
        case 'decided':
          decideError.value = 'Dieser Antrag wurde bereits entschieden. Die Liste wurde aktualisiert.'
          await load('open')
          break
        case 'conflict':
          decideError.value = 'Mindestens ein Wert hat sich seit dem Antrag geändert. Bestätige die Überschreibung ausdrücklich. Es wurde nichts übernommen.'
          break
        case 'own_request':
          decideError.value = 'Eigene Anträge gibt eine andere Person frei.'
          break
        case 'invalid':
          decideError.value = 'Bitte entscheide jedes Feld, bevor du speicherst.'
          break
        default:
          if (response?.status === 404) {
            decideError.value = 'Der Antrag ist nicht mehr verfügbar. Die Liste wurde aktualisiert.'
            await load('open')
          } else if (response?.status === 403) decideError.value = 'Dir fehlt die Berechtigung, diesen Antrag zu entscheiden.'
          else decideError.value = getApiErrorMessage(err, 'Die Entscheidung konnte nicht gespeichert werden.')
      }
      return false
    } finally {
      busy.value = false
    }
  }

  return { scope, open, decided, list, loading, error, selectedId, selected, busy, decideError, decideFields, notice, load, setScope, select, decide }
})
