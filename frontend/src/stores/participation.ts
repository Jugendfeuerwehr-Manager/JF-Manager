import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  participationApi,
  type ParticipationConfig, type ParticipationMode, type ReasonCategory, type RegistrationOverview,
  type RegistrationTarget, type Rule, type RuleErrors, type RulePreviewResult, type WaitlistMode,
} from '@/api/participation'
import { getApiErrorMessage } from '@/utils/apiError'

export const PREVIEW_DELAY_MS = 400
export const STALE_MESSAGE = 'Die Teilnahme-Einstellungen wurden zwischenzeitlich von jemand anderem geändert.'

export interface ConfigDraft {
  mode: ParticipationMode
  portal_visible: boolean
  public_note: string
  registration_opens_at: string | null
  registration_closes_at: string | null
  cancellation_closes_at: string | null
  max_participants: number | null
  min_participants: number | null
  waitlist_mode: WaitlistMode
  eligibility: Rule
}

export interface ActionResult { ok: boolean, code?: string, message?: string }

export const emptyRule = (): Rule => ({ v: 1, match: 'all', rules: [] })
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T

export function draftFrom(config: ParticipationConfig): ConfigDraft {
  const rule = config.eligibility as Rule | null
  return {
    mode: config.mode,
    portal_visible: config.portal_visible,
    public_note: config.public_note ?? '',
    registration_opens_at: config.registration_opens_at,
    registration_closes_at: config.registration_closes_at,
    cancellation_closes_at: config.cancellation_closes_at,
    max_participants: config.max_participants,
    min_participants: config.min_participants,
    waitlist_mode: config.waitlist_mode,
    eligibility: rule && 'rules' in rule ? clone(rule) : emptyRule(),
  }
}

interface ErrorBody { code?: string, detail?: string, current?: ParticipationConfig, errors?: RuleErrors }
const bodyOf = (err: unknown) => (err as { response?: { status?: number, data?: ErrorBody & Record<string, unknown> } }).response

/** `{eligibility: {path: msg}}` or `{field: ["msg"]}` of a 400 answer, flattened to `field -> message`. */
function fieldErrorsOf(data: Record<string, unknown> | undefined): { fields: Record<string, string>, rule: RuleErrors } {
  const fields: Record<string, string> = {}
  let rule: RuleErrors = {}
  for (const [key, value] of Object.entries(data ?? {})) {
    if (key === 'eligibility' && value && typeof value === 'object' && !Array.isArray(value)) {
      rule = value as RuleErrors
    } else if (Array.isArray(value) && typeof value[0] === 'string') {
      fields[key] = value[0]
    } else if (typeof value === 'string' && key !== 'detail' && key !== 'code') {
      fields[key] = value
    }
  }
  return { fields, rule }
}

export const useParticipationStore = defineStore('participation', () => {
  const sessionId = ref<number | null>(null)
  const config = ref<ParticipationConfig | null>(null)
  const draft = ref<ConfigDraft | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const fieldErrors = ref<Record<string, string>>({})
  const conflict = ref<ParticipationConfig | null>(null)
  const notice = ref<string | null>(null)

  const registrations = ref<RegistrationOverview | null>(null)
  const registrationsLoading = ref(false)
  const registrationsError = ref<string | null>(null)
  const busyMember = ref<number | null>(null)

  const ruleErrors = ref<RuleErrors>({})
  const preview = ref<RulePreviewResult | null>(null)
  const previewLoading = ref(false)
  const previewError = ref<string | null>(null)

  const dirty = computed(() => {
    if (!config.value || !draft.value) return false
    return JSON.stringify(draft.value) !== JSON.stringify(draftFrom(config.value))
  })

  let configSeq = 0
  let previewSeq = 0
  let previewTimer: ReturnType<typeof setTimeout> | null = null

  function adopt(next: ParticipationConfig, keepDraft = false) {
    config.value = next
    if (!keepDraft) draft.value = draftFrom(next)
    fieldErrors.value = {}
    ruleErrors.value = {}
  }

  function reset() {
    cancelPreview()
    sessionId.value = null
    config.value = null
    draft.value = null
    registrations.value = null
    conflict.value = null
    notice.value = null
    error.value = null
    preview.value = null
    ruleErrors.value = {}
    fieldErrors.value = {}
  }

  async function loadConfig(id: number) {
    if (sessionId.value !== id) reset()
    sessionId.value = id
    const seq = ++configSeq
    loading.value = true
    error.value = null
    try {
      const response = await participationApi.config(id)
      if (seq !== configSeq) return
      adopt(response.data)
      conflict.value = null
    } catch (err) {
      if (seq === configSeq) error.value = getApiErrorMessage(err, 'Die Teilnahme-Einstellungen konnten nicht geladen werden.')
    } finally {
      if (seq === configSeq) loading.value = false
    }
  }

  function setMode(mode: ParticipationMode) {
    if (!draft.value) return
    draft.value.mode = mode
    if (mode === 'opt_out') {
      // D5: places and waiting list only exist where people sign up.
      draft.value.max_participants = null
      draft.value.min_participants = null
    }
  }

  function discard() {
    if (config.value) adopt(config.value)
    notice.value = null
    conflict.value = null
  }

  function payload(current: ConfigDraft, revision: number) {
    const rule = current.eligibility
    return { ...current, eligibility: rule.rules.length ? rule : {}, revision }
  }

  async function saveConfig(): Promise<ActionResult> {
    if (!config.value || !draft.value || sessionId.value === null) return { ok: false }
    saving.value = true
    error.value = null
    notice.value = null
    fieldErrors.value = {}
    try {
      const response = await participationApi.saveConfig(sessionId.value, payload(draft.value, config.value.revision))
      adopt(response.data)
      conflict.value = null
      notice.value = 'Gespeichert.'
      void refreshRegistrationsQuietly()
      return { ok: true }
    } catch (err) {
      const response = bodyOf(err)
      if (response?.status === 409) {
        conflict.value = response.data?.current ?? null
        error.value = STALE_MESSAGE
        return { ok: false, code: 'stale', message: STALE_MESSAGE }
      }
      if (response?.status === 400) {
        const { fields, rule } = fieldErrorsOf(response.data)
        fieldErrors.value = fields
        ruleErrors.value = rule
        error.value = 'Bitte die markierten Angaben prüfen.'
        return { ok: false, code: 'invalid', message: error.value }
      }
      error.value = getApiErrorMessage(err, 'Speichern fehlgeschlagen.')
      return { ok: false, code: response?.data?.code, message: error.value }
    } finally {
      saving.value = false
    }
  }

  /** After a conflict: take the server version and drop the draft. */
  function useServerVersion() {
    if (conflict.value) adopt(conflict.value)
    conflict.value = null
    error.value = null
  }

  /** After a conflict: keep the draft, but save on top of the newer revision. */
  function keepDraftOnServerVersion() {
    if (conflict.value) adopt(conflict.value, true)
    conflict.value = null
    error.value = null
  }

  // ── Rule preview ──────────────────────────────────────────────────────

  function cancelPreview() {
    if (previewTimer) clearTimeout(previewTimer)
    previewTimer = null
    previewSeq++
    previewLoading.value = false
  }

  async function runPreview(rule: Rule): Promise<void> {
    if (sessionId.value === null) return
    const seq = ++previewSeq
    previewLoading.value = true
    previewError.value = null
    try {
      const response = await participationApi.preview(rule, sessionId.value)
      if (seq !== previewSeq) return
      preview.value = response.data
      ruleErrors.value = {}
    } catch (err) {
      if (seq !== previewSeq) return
      const response = bodyOf(err)
      if (response?.status === 400 && response.data?.errors) {
        ruleErrors.value = response.data.errors
        preview.value = null
      } else {
        previewError.value = getApiErrorMessage(err, 'Die Vorschau konnte nicht berechnet werden.')
      }
    } finally {
      if (seq === previewSeq) previewLoading.value = false
    }
  }

  /** Debounced: typing in a rule row triggers one request after a short pause. */
  function schedulePreview(rule: Rule) {
    if (previewTimer) clearTimeout(previewTimer)
    previewSeq++
    previewLoading.value = true
    const snapshot = clone(rule)
    previewTimer = setTimeout(() => { previewTimer = null; void runPreview(snapshot) }, PREVIEW_DELAY_MS)
  }

  // ── Registrations ─────────────────────────────────────────────────────

  async function loadRegistrations(id: number | null = sessionId.value) {
    if (id === null) return
    if (sessionId.value !== id) reset()
    sessionId.value = id
    registrationsLoading.value = true
    registrationsError.value = null
    try {
      registrations.value = (await participationApi.registrations(id)).data
    } catch (err) {
      registrationsError.value = getApiErrorMessage(err, 'Die Meldungen konnten nicht geladen werden.')
    } finally {
      registrationsLoading.value = false
    }
  }

  async function refreshRegistrationsQuietly() {
    if (registrations.value) await loadRegistrations()
  }

  async function setRegistration(
    memberId: number, target: RegistrationTarget, reason: { category?: ReasonCategory, note?: string } = {},
  ): Promise<ActionResult> {
    if (sessionId.value === null) return { ok: false }
    const row = registrations.value?.members.find(m => m.member_id === memberId)
    busyMember.value = memberId
    try {
      await participationApi.setRegistration(sessionId.value, memberId, {
        target,
        reason_category: reason.category ?? '',
        reason_note: reason.note ?? '',
        version: row?.registration?.version ?? null,
        accept_waitlist: true,
      })
      await loadRegistrations()
      return { ok: true }
    } catch (err) {
      const response = bodyOf(err)
      if (response?.status === 409) await loadRegistrations()
      return { ok: false, code: response?.data?.code, message: getApiErrorMessage(err, 'Die Meldung konnte nicht geändert werden.') }
    } finally {
      busyMember.value = null
    }
  }

  return {
    sessionId, config, draft, loading, saving, error, fieldErrors, conflict, notice, dirty,
    registrations, registrationsLoading, registrationsError, busyMember,
    ruleErrors, preview, previewLoading, previewError,
    loadConfig, setMode, discard, saveConfig, useServerVersion, keepDraftOnServerVersion,
    schedulePreview, runPreview, cancelPreview, loadRegistrations, setRegistration, reset,
  }
})
