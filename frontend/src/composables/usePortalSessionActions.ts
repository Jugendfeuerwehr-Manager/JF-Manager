import { computed, ref } from 'vue'
import type { PortalReason, PortalSessionItem } from '@/api/portal'
import { usePortalStore } from '@/stores/portal'
import type { SessionAction } from '@/utils/portalSessions'

/** Click handling shared by the overview, the list and the detail page. */
export function usePortalSessionActions() {
  const portal = usePortalStore()
  const sheetId = ref<number | null>(null)
  const sheetError = ref<string | null>(null)
  const sheetItem = computed(() => portal.sessions.find(s => s.id === sheetId.value) ?? null)

  async function run(item: PortalSessionItem, action: SessionAction) {
    if (action.opensSheet) {
      sheetId.value = item.id
      sheetError.value = null
      portal.actionError = null
      return
    }
    const payload: { target: SessionAction['target'], accept_waitlist?: boolean } = { target: action.target }
    // The label already announced the waitlist when the service is full.
    if (action.kind === 'register') payload.accept_waitlist = item.limited && item.free_places === 0
    await portal.setRegistration(item, payload)
  }

  async function submitCancel(payload: { reason_category: PortalReason | '', reason_note: string }) {
    const item = sheetItem.value
    if (!item) return
    sheetError.value = null
    const ok = await portal.setRegistration(item, { target: 'cancelled', ...payload })
    if (ok) sheetId.value = null
    else sheetError.value = portal.actionError?.message ?? 'Die Abmeldung konnte nicht gespeichert werden.'
  }

  function closeSheet() { sheetId.value = null; sheetError.value = null }

  return { sheetItem, sheetError, run, submitCancel, closeSheet }
}
