import type { Ref } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useTrainingStore } from '@/stores/training'

/** What deleting needs to know about an exercise (planner and phone view, FIX-05). */
export interface DeletableSession {
  id: number
  title: string
  linked_service_id: number | null
  linked_service_start: string | null
  requires_service_confirmation: boolean
}

/**
 * Confirm and delete an exercise, then return to the calendar. A future, undocumented linked
 * service-book entry can be deleted with it or kept and unlinked (same choice as in the calendar).
 */
export function useTrainingSessionDelete(session: Ref<DeletableSession | null | undefined>, onDeleted?: () => void) {
  const router = useRouter()
  const confirm = useConfirm()
  const toast = useToast()
  const trainingStore = useTrainingStore()

  function hasFutureLinkedService() {
    const s = session.value
    if (!s || s.requires_service_confirmation || !s.linked_service_id || !s.linked_service_start) return false
    return new Date(s.linked_service_start) >= new Date()
  }

  async function run(deleteLinkedService: boolean) {
    const s = session.value
    if (!s) return
    try {
      await trainingStore.deleteSession(s.id, { deleteLinkedService })
    } catch {
      toast.add({ severity: 'error', summary: 'Löschen fehlgeschlagen', detail: 'Die Übung konnte nicht gelöscht werden.', life: 5000 })
      return
    }
    onDeleted?.()
    toast.add({ severity: 'success', summary: 'Übung gelöscht', life: 3000 })
    void router.push('/training')
  }

  function confirmDelete() {
    const s = session.value
    if (!s) return
    const consequence = 'Plan, Teilnahme-Einstellungen und alle Meldungen werden endgültig entfernt; Teilnehmende werden nicht benachrichtigt. Zum Informieren stattdessen „Absagen“ wählen.'
    if (hasFutureLinkedService()) {
      confirm.require({
        header: 'Übung und verknüpften Dienst löschen?',
        message: `${consequence} Diese Übung ist mit einem zukünftigen Dienstbuch-Eintrag verknüpft: „Mit Dienstbuch löschen“ entfernt beide, „Nur Übung löschen“ entkoppelt den Eintrag.`,
        icon: 'pi pi-exclamation-triangle',
        acceptLabel: 'Mit Dienstbuch löschen',
        rejectLabel: 'Nur Übung löschen',
        acceptClass: 'p-button-danger',
        accept: () => { void run(true) },
        reject: () => { void run(false) },
      })
      return
    }
    confirm.require({
      header: `„${s.title}“ löschen?`,
      message: consequence,
      icon: 'pi pi-exclamation-triangle',
      acceptLabel: 'Löschen',
      rejectLabel: 'Abbrechen',
      acceptClass: 'p-button-danger',
      accept: () => { void run(false) },
    })
  }

  return { confirmDelete }
}
