import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { portalApi, type PortalAbsencePayload, type PortalAbsencePreviewRow, type PortalAbsenceResult, type PortalRegistrationPayload, type PortalSessionItem, type PortalMe, type PortalPersonData, type InvitationInfo, type AcceptInvitationPayload } from '@/api/portal'
import { getApiErrorMessage } from '@/utils/apiError'

export interface PortalActionError { status?: number, code: string, message: string, reasons: string[], sessionId?: number }

export const usePortalStore = defineStore('portal', () => {
  const me = ref<PortalMe | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const selectedPersonId = ref<number | null>(null)
  const selectedPerson = computed(() => me.value?.people.find(p => p.id === selectedPersonId.value) ?? null)

  function selectPerson(id: number) {
    if (me.value?.people.some(p => p.id === id)) selectedPersonId.value = id
  }

  const personData = ref<PortalPersonData | null>(null)
  const personLoading = ref(false)
  const personError = ref<{ status?: number, message: string } | null>(null)
  let personSeq = 0

  /** Released data of one person; only the newest request may write (the switcher changes quickly). */
  async function loadPerson(id: number | null) {
    const seq = ++personSeq
    personData.value = null
    personError.value = null
    if (id === null) { personLoading.value = false; return }
    personLoading.value = true
    try {
      const { data } = await portalApi.person(id)
      if (seq === personSeq) personData.value = data
    } catch (err) {
      if (seq !== personSeq) return
      const status = (err as { response?: { status?: number } }).response?.status
      personError.value = {
        status,
        message: status === 404 ? 'Für diese Person sind keine Daten verfügbar.' : getApiErrorMessage(err, 'Die Daten konnten nicht geladen werden.'),
      }
    } finally {
      if (seq === personSeq) personLoading.value = false
    }
  }

  // Planned services of the selected person
  const sessions = ref<PortalSessionItem[]>([])
  const sessionsPersonId = ref<number | null>(null)
  const sessionsLoaded = ref(false)
  const sessionsLoading = ref(false)
  const sessionsError = ref<string | null>(null)
  const pendingSessionIds = ref<number[]>([])
  const actionError = ref<PortalActionError | null>(null)
  let sessionsSeq = 0

  function status(err: unknown): number | undefined {
    return (err as { response?: { status?: number } }).response?.status
  }

  /** Newest request wins; the list always belongs to `sessionsPersonId`. */
  async function loadSessions(personId: number | null = selectedPersonId.value) {
    const seq = ++sessionsSeq
    if (personId !== sessionsPersonId.value) { sessions.value = []; sessionsLoaded.value = false; actionError.value = null }
    sessionsPersonId.value = personId
    sessionsError.value = null
    if (personId === null) { sessionsLoading.value = false; return }
    sessionsLoading.value = true
    try {
      const { data } = await portalApi.sessions(personId)
      if (seq !== sessionsSeq) return
      sessions.value = data.sessions
      sessionsLoaded.value = true
    } catch (err) {
      if (seq !== sessionsSeq) return
      sessionsError.value = status(err) === 429 ? 'Bitte kurz warten und erneut versuchen.' : getApiErrorMessage(err, 'Die Termine konnten nicht geladen werden.')
    } finally {
      if (seq === sessionsSeq) sessionsLoading.value = false
    }
  }

  function describeActionError(err: unknown, fallback: string): PortalActionError {
    const code = status(err)
    const data = (err as { response?: { data?: { code?: string, detail?: string, reasons?: string[] } } }).response?.data
    if (code === 429) return { status: code, code: 'throttled', message: 'Bitte kurz warten und erneut versuchen.', reasons: [] }
    if (code === 409) return { status: code, code: 'stale', message: 'Die Meldung wurde inzwischen geändert. Die Ansicht wurde aktualisiert, bitte prüfe sie und versuche es erneut.', reasons: [] }
    return { status: code, code: data?.code ?? 'error', message: getApiErrorMessage(err, fallback), reasons: Array.isArray(data?.reasons) ? data.reasons : [] }
  }

  /**
   * Sends one change for the selected person. The list is only updated with what the server
   * answered; a 409 or 422 reloads it so the offered actions match the server's view.
   */
  async function setRegistration(item: PortalSessionItem, payload: PortalRegistrationPayload): Promise<boolean> {
    const personId = selectedPersonId.value
    if (personId === null || pendingSessionIds.value.includes(item.id)) return false
    pendingSessionIds.value = [...pendingSessionIds.value, item.id]
    actionError.value = null
    try {
      const { data } = await portalApi.setRegistration(item.id, personId, { version: item.version, ...payload })
      if (sessionsPersonId.value === personId) sessions.value = sessions.value.map(s => (s.id === data.id ? data : s))
      return true
    } catch (err) {
      const failure = describeActionError(err, 'Die Meldung konnte nicht gespeichert werden.')
      if (failure.status === 409 || failure.status === 422) await loadSessions(personId)
      actionError.value = { ...failure, sessionId: item.id }
      return false
    } finally {
      pendingSessionIds.value = pendingSessionIds.value.filter(id => id !== item.id)
    }
  }

  const absencePreview = ref<PortalAbsencePreviewRow[] | null>(null)
  const absenceBusy = ref(false)
  const absenceError = ref<string | null>(null)

  function absenceFailure(err: unknown, fallback: string) {
    return status(err) === 429 ? 'Bitte kurz warten und erneut versuchen.' : getApiErrorMessage(err, fallback)
  }

  async function previewAbsence(range: Omit<PortalAbsencePayload, 'person'>): Promise<boolean> {
    const person = selectedPersonId.value
    absencePreview.value = null
    absenceError.value = null
    if (person === null) return false
    absenceBusy.value = true
    try {
      absencePreview.value = (await portalApi.previewAbsence({ ...range, person })).data.sessions
      return true
    } catch (err) {
      absenceError.value = absenceFailure(err, 'Die Vorschau konnte nicht geladen werden.')
      return false
    } finally {
      absenceBusy.value = false
    }
  }

  async function createAbsence(range: Omit<PortalAbsencePayload, 'person'>): Promise<PortalAbsenceResult | null> {
    const person = selectedPersonId.value
    absenceError.value = null
    if (person === null) return null
    absenceBusy.value = true
    try {
      const result = (await portalApi.createAbsence({ ...range, person })).data
      await loadSessions(person)
      return result
    } catch (err) {
      absenceError.value = absenceFailure(err, 'Die Abmeldung konnte nicht gespeichert werden.')
      return null
    } finally {
      absenceBusy.value = false
    }
  }

  function resetAbsence() { absencePreview.value = null; absenceError.value = null }

  async function fetchMe() {
    loading.value = true
    error.value = null
    try {
      me.value = (await portalApi.me()).data
      if (!me.value.people.some(p => p.id === selectedPersonId.value)) {
        selectedPersonId.value = me.value.people[0]?.id ?? null
      }
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Die Daten konnten nicht geladen werden.')
    } finally {
      loading.value = false
    }
  }

  // Invitation acceptance (public page)
  const invitation = ref<InvitationInfo | null>(null)
  const invitationLoading = ref(false)
  const invitationError = ref<{ code: string, message: string } | null>(null)
  const acceptFieldErrors = ref<Record<string, string>>({})
  const acceptError = ref<string | null>(null)
  const accepting = ref(false)
  const accepted = ref(false)

  function errorPayload(err: unknown) {
    const e = err as { response?: { status?: number, data?: Record<string, unknown> } }
    return { status: e.response?.status, data: e.response?.data }
  }

  async function loadInvitation(token: string) {
    invitation.value = null
    accepted.value = false
    invitationError.value = null
    if (!token) {
      invitationError.value = { code: 'invalid', message: 'Dieser Einladungslink ist ungültig.' }
      return
    }
    invitationLoading.value = true
    try {
      invitation.value = (await portalApi.invitationInfo(token)).data
    } catch (err) {
      const { status, data } = errorPayload(err)
      const code = status === 429 ? 'throttled' : typeof data?.code === 'string' ? data.code : 'error'
      invitationError.value = {
        code,
        message: getApiErrorMessage(err, 'Die Einladung konnte nicht geprüft werden.'),
      }
    } finally {
      invitationLoading.value = false
    }
  }

  async function acceptInvitation(payload: AcceptInvitationPayload) {
    accepting.value = true
    acceptError.value = null
    acceptFieldErrors.value = {}
    try {
      await portalApi.acceptInvitation(payload)
      accepted.value = true
      return true
    } catch (err) {
      const { status, data } = errorPayload(err)
      if (status === 400 && data) {
        const fields: Record<string, string> = {}
        for (const [key, value] of Object.entries(data)) {
          if (key === 'code') continue
          const text = Array.isArray(value) ? String(value[0]) : typeof value === 'string' ? value : ''
          if (text) fields[key] = text
        }
        acceptFieldErrors.value = fields
        if (!Object.keys(fields).length) acceptError.value = 'Bitte prüfe deine Eingaben.'
      } else {
        const code = typeof data?.code === 'string' ? data.code : ''
        if (code === 'invalid' || code === 'expired') {
          invitationError.value = { code, message: getApiErrorMessage(err, 'Die Einladung ist nicht mehr gültig.') }
        }
        acceptError.value = getApiErrorMessage(err, 'Der Zugang konnte nicht eingerichtet werden.')
      }
      return false
    } finally {
      accepting.value = false
    }
  }

  return {
    sessions, sessionsPersonId, sessionsLoaded, sessionsLoading, sessionsError, pendingSessionIds, actionError, loadSessions, setRegistration,
    absencePreview, absenceBusy, absenceError, previewAbsence, createAbsence, resetAbsence,
    me, loading, error, fetchMe, personData, personLoading, personError, loadPerson, selectedPersonId, selectedPerson, selectPerson,
    invitation, invitationLoading, invitationError, loadInvitation,
    accepting, accepted, acceptError, acceptFieldErrors, acceptInvitation,
  }
})
