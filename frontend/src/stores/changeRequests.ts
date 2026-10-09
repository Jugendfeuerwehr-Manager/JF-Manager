import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { changeRequestsApi } from '@/api/changeRequests'
import type { ChangeRequest, ChangeRequestErrorBody, ChangeTarget } from '@/types/changeRequests'
import { matchesTarget } from '@/utils/changeRequestFields'
import { getApiErrorMessage } from '@/utils/apiError'

function errorBody(err: unknown): { status?: number, body: ChangeRequestErrorBody } {
  const response = (err as { response?: { status?: number, data?: ChangeRequestErrorBody } }).response
  return { status: response?.status, body: response?.data ?? {} }
}

/** Portal side: own change requests (PORTAL-03.2). */
export const useChangeRequestsStore = defineStore('changeRequests', () => {
  const requests = ref<ChangeRequest[]>([])
  const loading = ref(false)
  const loaded = ref(false)
  const busy = ref(false)
  const formError = ref<string | null>(null)
  const fieldErrors = ref<Record<string, string>>({})
  const actionError = ref<string | null>(null)

  async function load() {
    loading.value = true
    try {
      requests.value = (await changeRequestsApi.list()).data.results
      loaded.value = true
    } catch {
      // Requests are an add-on of the data page: the page itself stays usable without them.
      requests.value = []
    } finally {
      loading.value = false
    }
  }

  const forTarget = (target: ChangeTarget | null) => (target ? requests.value.filter(r => matchesTarget(r, target)) : [])
  const openFor = (target: ChangeTarget | null) => forTarget(target).find(r => r.status === 'open') ?? null
  /** Newest decided request; withdrawn ones are not an outcome worth reporting. */
  const decidedFor = (target: ChangeTarget | null) =>
    forTarget(target).find(r => r.status === 'applied' || r.status === 'partial' || r.status === 'rejected') ?? null
  const hasOpen = computed(() => requests.value.some(r => r.status === 'open'))

  function resetErrors() { formError.value = null; fieldErrors.value = {}; actionError.value = null }

  function upsert(request: ChangeRequest) {
    requests.value = [request, ...requests.value.filter(r => r.id !== request.id)]
  }

  /** Sends only the changed fields; returns true when the server accepted the request. */
  async function submit(target: ChangeTarget, fields: Record<string, string>): Promise<boolean> {
    if (busy.value) return false
    busy.value = true
    resetErrors()
    try {
      upsert((await changeRequestsApi.submit(target, fields)).data)
      return true
    } catch (err) {
      const { status, body } = errorBody(err)
      fieldErrors.value = body.fields ?? {}
      if (body.code === 'unchanged') formError.value = 'Du hast nichts geändert. Die Daten stimmen schon mit deinem Antrag überein.'
      else if (status === 429) formError.value = 'Bitte kurz warten und erneut versuchen.'
      else if (status === 404) formError.value = 'Diese Person ist nicht mehr verfügbar.'
      else if (body.code === 'conflict') formError.value = body.detail ?? 'Der Antrag wurde inzwischen geändert. Bitte versuche es erneut.'
      else formError.value = Object.keys(fieldErrors.value).length
        ? 'Bitte prüfe die markierten Felder.'
        : getApiErrorMessage(err, 'Der Antrag konnte nicht gesendet werden.')
      return false
    } finally {
      busy.value = false
    }
  }

  async function withdraw(id: number): Promise<boolean> {
    if (busy.value) return false
    busy.value = true
    resetErrors()
    try {
      upsert((await changeRequestsApi.withdraw(id)).data)
      return true
    } catch (err) {
      const { status } = errorBody(err)
      actionError.value = status === 409
        ? 'Der Antrag wurde schon entschieden und kann nicht mehr zurückgezogen werden.'
        : getApiErrorMessage(err, 'Der Antrag konnte nicht zurückgezogen werden.')
      if (status === 409) await load()
      return false
    } finally {
      busy.value = false
    }
  }

  return { requests, loading, loaded, busy, formError, fieldErrors, actionError, hasOpen, load, forTarget, openFor, decidedFor, submit, withdraw, resetErrors }
})
