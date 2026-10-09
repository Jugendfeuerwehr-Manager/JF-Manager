import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  participationApi, staffingTemplatesApi,
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
  extra_places: number | null
  slots: SlotDraft[]
}

/** A position while editing; `key` keeps list rendering stable for new rows without id. */
export interface SlotDraft { key: string, id: number | null, label: string, min: number, max: number, rule: Rule }

let slotKeys = 0
export function newSlotDraft(label = ''): SlotDraft {
  return { key: `new-${++slotKeys}`, id: null, label, min: 0, max: 1, rule: emptyRule() }
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
    extra_places: config.extra_places ?? null,
    slots: (config.slots ?? []).map(slot => ({
      key: `slot-${slot.id}`,
      id: slot.id,
      label: slot.label,
      min: slot.min,
      max: slot.max,
      rule: slot.rule && 'rules' in slot.rule ? clone(slot.rule as Rule) : emptyRule(),
    })),
  }
}

/** Places derived from the positions (concept 4.7) or the plain maximum. */
export function draftCapacity(draft: ConfigDraft): number | null {
  if (!draft.slots.length) return draft.max_participants
  return draft.slots.reduce((sum, slot) => sum + (Number(slot.max) || 0), 0) + (draft.extra_places ?? 0)
}

interface ErrorBody { code?: string, detail?: string, current?: ParticipationConfig, errors?: RuleErrors }
const bodyOf = (err: unknown) => (err as { response?: { status?: number, data?: ErrorBody & Record<string, unknown> } }).response

/** `{eligibility: {path: msg}}` or `{field: ["msg"]}` of a 400 answer, flattened to `field -> message`. */
function fieldErrorsOf(data: Record<string, unknown> | undefined): { fields: Record<string, string>, rule: RuleErrors } {
  const fields: Record<string, string> = {}
  let rule: RuleErrors = {}
  for (const [key, value] of Object.entries(data ?? {})) {
    if (key === 'slots' && Array.isArray(value) && value.some(item => item && typeof item === 'object')) {
      value.forEach((item, index) => {
        if (!item || typeof item !== 'object') return
        for (const [field, message] of Object.entries(item as Record<string, unknown>)) {
          if (field === 'rule' && message && typeof message === 'object' && !Array.isArray(message)) {
            for (const [path, text] of Object.entries(message as Record<string, string>)) fields[`slots[${index}].rule.${path}`] = String(text)
          } else {
            fields[`slots[${index}].${field}`] = Array.isArray(message) ? String(message[0]) : String(message)
          }
        }
      })
    } else if (key === 'eligibility' && value && typeof value === 'object' && !Array.isArray(value)) {
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
      // D5: places, positions and waiting list only exist where people sign up.
      draft.value.max_participants = null
      draft.value.min_participants = null
      draft.value.slots = []
      draft.value.extra_places = null
    }
  }

  function discard() {
    if (config.value) adopt(config.value)
    notice.value = null
    conflict.value = null
  }

  function payload(current: ConfigDraft, revision: number) {
    const rule = current.eligibility
    const slots = current.slots.map(slot => ({
      id: slot.id, label: slot.label.trim(), min: Number(slot.min) || 0, max: Number(slot.max) || 0,
      rule: slot.rule.rules.length ? slot.rule : {},
    }))
    return { ...current, slots, eligibility: rule.rules.length ? rule : {}, revision }
  }

  /** Copy a staffing template into this service (PART-04.5); the server answers with the new configuration. */
  async function applyTemplate(templateId: number): Promise<ActionResult & { warnings?: string[] }> {
    if (!config.value || sessionId.value === null) return { ok: false }
    saving.value = true
    error.value = null
    notice.value = null
    try {
      const response = await staffingTemplatesApi.apply(sessionId.value, templateId, config.value.revision)
      const { warnings, ...next } = response.data
      adopt(next)
      notice.value = `Vorlage „${next.template_source?.name ?? ''}“ übernommen.`
      void refreshRegistrationsQuietly()
      return { ok: true, warnings }
    } catch (err) {
      const response = bodyOf(err)
      if (response?.status === 409) {
        conflict.value = response.data?.current ?? null
        error.value = STALE_MESSAGE
        return { ok: false, code: 'stale', message: STALE_MESSAGE }
      }
      error.value = getApiErrorMessage(err, 'Die Vorlage konnte nicht übernommen werden.')
      const reasons = (response?.data as { reasons?: string[] } | undefined)?.reasons
      return { ok: false, code: response?.data?.code, message: [error.value, ...(reasons ?? [])].join(' ') }
    } finally {
      saving.value = false
    }
  }

  function addSlot(label = '') {
    if (!draft.value) return
    draft.value.slots.push(newSlotDraft(label))
  }

  function removeSlot(index: number) {
    draft.value?.slots.splice(index, 1)
  }

  function moveSlot(index: number, delta: -1 | 1) {
    const list = draft.value?.slots
    const target = index + delta
    if (!list || target < 0 || target >= list.length) return
    const [item] = list.splice(index, 1)
    list.splice(target, 0, item!)
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
    loadConfig, setMode, discard, saveConfig, applyTemplate, addSlot, removeSlot, moveSlot, useServerVersion, keepDraftOnServerVersion,
    schedulePreview, runPreview, cancelPreview, loadRegistrations, setRegistration, reset,
  }
})
