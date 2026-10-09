import { computed, ref } from 'vue'
import { isAxiosError } from 'axios'
import { actionsApi, type ActionErrorBody, type ActionPreview, type ActionResult } from '@/api/actions'

export type QuickActionPhase = 'loading' | 'confirm' | 'result' | 'error'

/** State machine behind `/a/:token`: resolve, execute directly or after confirmation, report the outcome. */
export function useQuickAction(token: () => string) {
  const phase = ref<QuickActionPhase>('loading')
  const preview = ref<ActionPreview | null>(null)
  const result = ref<ActionResult | null>(null)
  const error = ref<ActionErrorBody | null>(null)
  const busy = ref(false)

  function fail(e: unknown) {
    const body = isAxiosError(e) ? (e.response?.data as Partial<ActionErrorBody> | undefined) : undefined
    error.value = {
      code: body?.code ?? ('failed' as ActionErrorBody['code']),
      detail: body?.detail ?? 'Die Aktion konnte nicht ausgeführt werden. Bitte versuche es erneut.',
      target_route: body?.target_route ?? '/',
    }
    phase.value = 'error'
  }

  async function execute(payload: Record<string, string> = {}) {
    busy.value = true
    try {
      result.value = (await actionsApi.execute(token(), payload)).data
      phase.value = 'result'
    } catch (e) {
      fail(e)
    } finally {
      busy.value = false
    }
  }

  /** Resolves the link; direct and ready actions run at once (they have no consequences). */
  async function start() {
    phase.value = 'loading'
    try {
      preview.value = (await actionsApi.resolve(token())).data
    } catch (e) {
      fail(e)
      return
    }
    if (preview.value.mode === 'direct' && preview.value.state === 'ready') await execute()
    else if (preview.value.state === 'ready') phase.value = 'confirm'
    else {
      result.value = { action: preview.value.action, mode: preview.value.mode, state: preview.value.state, lines: preview.value.lines, target_route: preview.value.target_route }
      phase.value = 'result'
    }
  }

  /** Takes a direct action back, e.g. an unsubscribe. */
  async function undo() {
    const undoToken = result.value?.undo?.token
    if (!undoToken) return
    busy.value = true
    try {
      const reverted = (await actionsApi.execute(undoToken)).data
      result.value = { ...reverted, undo: undefined }
    } catch (e) {
      fail(e)
    } finally {
      busy.value = false
    }
  }

  const targetRoute = computed(() => result.value?.target_route ?? preview.value?.target_route ?? error.value?.target_route ?? '/')

  return { phase, preview, result, error, busy, targetRoute, start, execute, undo }
}
