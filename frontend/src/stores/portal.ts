import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { portalApi, type PortalMe, type InvitationInfo, type AcceptInvitationPayload } from '@/api/portal'
import { getApiErrorMessage } from '@/utils/apiError'

export const usePortalStore = defineStore('portal', () => {
  const me = ref<PortalMe | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const selectedPersonId = ref<number | null>(null)
  const selectedPerson = computed(() => me.value?.people.find(p => p.id === selectedPersonId.value) ?? null)

  function selectPerson(id: number) {
    if (me.value?.people.some(p => p.id === id)) selectedPersonId.value = id
  }

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
    me, loading, error, fetchMe, selectedPersonId, selectedPerson, selectPerson,
    invitation, invitationLoading, invitationError, loadInvitation,
    accepting, accepted, acceptError, acceptFieldErrors, acceptInvitation,
  }
})
